#!/usr/bin/env python3
from __future__ import print_function
import os
import sys
import re
import argparse
import frontmatter
from datetime import datetime
import getpass
import time
from sys import exit
from wordpress import API

# This imports markdown files into wordpress
def wp_import(folder):
	# Set our headers
	headers = { 'content-type': 'application/json; charset=UTF-8' }
	
	# load site categories
	site_categories = get_site_taxonomy('categories')

	# load site tags
	site_tags = get_site_taxonomy('tags')

	for subdir, dirs, files in os.walk(folder):
		for file in files:
			
			filepath = subdir + os.sep + file
			
			if filepath.endswith(".markdown") or filepath.endswith(".md") or filepath.endswith(".mdown"):
				# Sleep for 5 seconds to prevent 429 Too many requests
				time.sleep(5)
				
				# load YAML frontmatter for current post
				try:
					fm = frontmatter.load(filepath)
				except Exception as e:
					print("Cannot parse YAML frontmatter for %s!, skipping." % (filepath))
	            				
	            # Are we importing a post or a page?
				if fm['layout'] == 'post':

					print("Importing Post: %s ..." % fm['title'])

					# Initialize our data dictionary
					data = {}

					# Ensure we have at minimum the title and content, or else continue to next file
					if fm['title'] is None or fm.content is None:
						print("Post does not have a title or content, skipping.", end='')
						continue
					
					# Set our title
					data['title'] = fm['title']

	            	# Content
	            	# We regex replace {: .class #id } jekyll notation to:
	            	# { .class #id } WordPress notation
					data['content'] = re.sub(r"{:(.*)}",r"{\1}", fm.content)

					# Date
					try:
						if fm['date'] is not None:
							post_date = datetime.strptime(fm['date'], "%Y-%m-%d %H:%M")
							data['date'] = str(post_date)
					except:
						print("Exception! Date format invalid. It should be YYYY-MM-DD HH:MM")
					
					# Slug
					if fm['slug'] is not None:
						data['slug'] = fm['slug']
	            
 					# Categories
					if fm['categories'] is not None:
						if isinstance(fm['categories'], str):
							fm['categories'] = fm['categories'].split(',') 
						
						data['categories'] = []
						
						for c in fm['categories']:
							if c.strip() in site_categories:
								data['categories'].append(site_categories[c.strip()])
							else:
								try:
									c_temp = {}
									c_temp['name'] = c.strip()
									r = wp.post("categories", c_temp, headers=headers)
									data['categories'].append(r.json()['id'])
								
									# reload site categories since we added one
									site_categories = get_site_taxonomy('categories')
								except Exception as e:
									print("Error!")
					
					if fm['tags'] is not None:
						if isinstance(fm['tags'], str):
							fm['tags'] = fm['tags'].split(',') 
						
						data['tags'] = []
						
						for t in fm['tags']:
							if t.strip() in site_tags:
								data['tags'].append(site_tags[t.strip()])
							else:
								try:
									t_temp = {}
									t_temp['name'] = t.strip()
									r = wp.post("tags", t_temp, headers=headers)
									data['tags'].append(r.json()['id'])
								
									# reload site tags since we added one
									site_tags = get_site_taxonomy('tags')
								except Exception as e:
									print("Error adding new tag '%s': %s" % (t_temp['name'], e))

						            	            
					# Make sure we set our post to "published"
					data['status'] = 'publish'
										
					# Check to see if we have a linked post or regular post and set accordingly
					if fm['type'] == 'link':
						data['format'] = "link"
						if fm['external-url']:
							data['meta'] = { 'external_url': fm['external-url'] }
						else:
							print("WARNING: Expected external-url for post type Link, did not find.")
						
					# Set our headers
					headers = { 'content-type': 'application/json; charset=UTF-8' }

					# Submit new post					
					try:
						wp.post("posts", data, headers=headers)
					except Exception as e:
						print("Error importing %s: %s" % (fm['title'], e))
					
				elif fm['layout'] == 'page':
					
					# Start import
					print("Importing Page: %s ..." % fm['title'])

					# Initialize our data dictionary
					data = {}

					# Ensure we have at minimum the title and content, or else continue to next file
					if fm['title'] is None or fm.content is None:
						print("Post does not have a title or content, skipping.", end='')
						continue
					
					# Set our title
					data['title'] = fm['title']

	            	# Content
	            	# We regex replace {: .class #id } jekyll notation to:
	            	# { .class #id } WordPress notation
					data['content'] = re.sub(r"{:(.*)}",r"{\1}", fm.content)

					# Date
					try:
						if fm['date'] is not None:
							post_date = datetime.strptime(fm['date'], "%Y-%m-%d %H:%M")
							data['date'] = str(post_date)
					except:
						print("Exception! Date format invalid. It should be YYYY-MM-DD HH:MM")
					
					# Slug
					if fm['slug'] is not None:
						data['slug'] = fm['slug']

					# Make sure we set our post to "published"
					data['status'] = 'publish'

					# Set our headers
					headers = { 'content-type': 'application/json; charset=UTF-8' }

					# Submit new post					
					try:
						wp.post("pages", data, headers=headers)
					except Exception as e:
						print("error! %s" % e)
					
				else:
					
					print("Layout not detected for %s, skipping." % file)

def wp_export(folder):

	if not os.path.exists(folder):
		try:
			os.makedirs(folder)
		except:
			print("Folder '%s' not writeable, exiting." % folder)
			exit()

	# Let's deal with posts first	
	offset = 0
	increment = 10

	while True:
		r = wp.get("posts",params={'per_page': increment, 'offset': offset})
		posts = r.json()
		print(posts)
		if len(posts) == 0:
			break # no more posts to query
			
		for post in posts:
			# Prepare Post Title
			post_title = post.get('title')
			
			# Format date
			post_date_raw = datetime.strptime(post.get('date'), '%Y-%m-%dT%H:%M:%S')
			post_date = post_date_raw.strftime('%Y-%m-%d %H:%M')
	
			# Get categories
			post_categories = ''
			for i, c in enumerate(post.get('categories')):
				rc = wp.get('categories/%s' % c)
				category = rc.json() 
				if i == 0:
					post_categories = post_categories + category['name']
				else:
					post_categories = post_categories + ", " + category['name']
	
			# Get tags
			post_tags = ''
			for i, t in enumerate(post.get('tags')):
				rt = wp.get('tags/%s' % t)
				tag = rt.json()
				
				if i == 0:
					post_tags = post_tags + tag['name']
				else:
					post_tags = post_tags + ", " + tag['name']
	
			# Build published status
			if post.get('status') == 'publish':
				post_status = "true"
			else:
				post_status = "false"
	
			# Get Post Author
			#a = wp.get(user_id=post.get('author'))
			ra = wp.get('users/%s' % post.get('author'))
			a = ra.json()
			post_author = a['name']
						
			# Build output		                
			output = "---\n"
			output = output + "layout: post\n"
			output = output + "type: %s\n" % post.get('format')
			output = output + "title: %s\n" % post_title['rendered']
			output = output + "date: %s\n" % post_date
			output = output + "author: %s\n" % post_author
			output = output + 'categories: %s\n' % post_categories
			output = output + 'tags: %s\n' % post_tags
			output = output + 'slug: %s\n' % post.get('slug')
			output = output + 'published: %s\n' % post_status
			
			# Build custom fields, each as key: value output
			cf = post.get('custom_fields')
			if cf:				
				for k, v in cf.iteritems():
					# Ignore _wp custom fields
					if not k.startswith('_'):
						output = output + "%s: " % k
						output = output + v[0] + "\n"
	
			# Finish output and add content
			output = output + "---\n"
			output = output + post.get('content-raw')
	
			# Let's write our markdown file!
			path = "%s/posts/" % folder
			os.makedirs(path, exist_ok=True)
			file = '%s-%s.markdown' % (post_date_raw.strftime('%Y-%m-%d'), post.get('slug'))
			#file = path + "/" + post_date_raw.strftime('%Y-%m-%d') + "-" + post.get('slug') + ".markdown"
			print("Writing post to file: %s%s" % (path, file))
			#f = open('%s%s' % (path, file), 'w')
			#f.write(output)
			#f.close

			# End of post loop
			
		# Increase our offset
		offset = offset + increment
		
		# End of while True loop
	
	# Now let's tackle pages
	offset = 0
	increment = 10

	while True:
		r = wp.get("pages",params={'per_page': increment, 'offset': offset})
		pages = r.json()
		if len(pages) == 0:
			break # no more posts to query
			
		for page in pages:
			# Prepare Post Title
			page_title = page.get('title')
			
			# Format date
			page_date_raw = datetime.strptime(page.get('date'), '%Y-%m-%dT%H:%M:%S')
			page_date = page_date_raw.strftime('%Y-%m-%d %H:%M')

			# Check content is not protected
			content_json = page.get('content')
			if not content_json['protected'] == True:
				page_content = page.get('content-raw')
					
			# Build published status
			if page.get('status') == 'publish':
				page_status = "true"
			else:
				page_status = "false"
			
			# Build permalink
			page_link_raw = page.get('link')
			page_permalink = re.sub(r"http(s?)://[^\/]*",r"", page_link_raw)
			
			# Get Page Author
			ra = wp.get('users/%s' % page.get('author'))
			a = ra.json()
			page_author = a['name']
						
			# Build output		                
			output = "---\n"
			output = output + 'layout: page\n'
			output = output + 'title: %s\n' % page_title['rendered']
			output = output + 'date: %s\n' % page_date
			output = output + 'author: %s\n' % page_author
			output = output + 'slug: %s\n' % page.get('slug')
			output = output + 'permalink: %s\n' % page_permalink
			output = output + 'published: %s\n' % page_status
			
			# Build custom fields, each as key: value output
			cf = page.get('custom_fields')
			if cf:				
				for k, v in cf.iteritems():
					# Ignore _wp custom fields
					if not k.startswith('_'):
						output = output + "%s: " % k
						output = output + v[0] + "\n"
	
			# Finish output and add content
			output = output + "---\n"
			output = output + page_content
	
			# Let's write our markdown file!
			path = "%s/pages%s" % (folder, page_permalink)
			file = "%s.markdown" % page.get('slug')
			os.makedirs(path, exist_ok=True)
			print("Writing page to file: %s%s" % (path, file))
			f = open('%s%s' % (path, file), 'w')
			f.write(output)
			f.close

			# End of post loop
			
		# Increase our offset
		offset = offset + increment
		
		# End of while True loop
		
def get_site_taxonomy(taxonomy):
	
	taxonomies = {}
	
	if taxonomy == "categories":
		# Currently only supports 100 categories
		# Need to implement pagination!
		r =  wp.get("categories/?per_page=100").json()
	elif taxonomy == 'tags':
		# Currently only supports 100 tags
		# Need to implement pagination!
		r = wp.get('tags/?per_page=100').json()
		
	for k in r:
		taxonomies[k['name']] = k['id']
	
	return taxonomies
		
		
if __name__ == "__main__":

	parser = argparse.ArgumentParser(prog="md2wp", description="Small program to import Jekyll-formatted markdown posts & pages to WordPress.")

	# Example
	# md2wp -u admin -p password -s https://mysite.com/ -f /home/jekyll/_posts
	parser.add_argument("-u", "--username", dest = "username", metavar="username", help="WordPress admin user", required=True)
	parser.add_argument("-s", "--site", dest = "site", metavar="site", help="WordPress site URL (ex: http://mysite.com)", required=True)
	parser.add_argument("-f", "--folder", dest = "folder", metavar="folder", help="Folder containing jekyll-formatted markdown posts", required=True)
	
	args = parser.parse_args()
	passwd = getpass.getpass('Password for %s:' % args.username)
	
	wp = API(
		url=args.site,
		consumer_key="",
		consumer_secret="",
		api="wp-json",
		version='wp/v2',
		wp_user=args.username,
		wp_pass=passwd,
		basic_auth = True,
		user_auth = True,
	)

	wp_import(args.folder)
