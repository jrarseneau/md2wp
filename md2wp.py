#!/usr/bin/env python3
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
	for subdir, dirs, files in os.walk(folder):
		for file in files:
			
			filepath = subdir + os.sep + file
			
			if filepath.endswith(".markdown") or filepath.endswith(".md") or filepath.endswith(".mdown"):
				# Sleep for 5 seconds to prevent 429 Too many requests
				time.sleep(5)
				
				# load YAML frontmatter for current post
				fm = frontmatter.load(filepath)
	            
	            # Are we importing a post or a page?
				if fm['layout'] == 'post':
	
					# create new post from source post content
					newpost = WordPressPost()
		            
					# Set the easy values
					newpost.title = fm['title']
					newpost.date = datetime.datetime.strptime(fm['date'], "%Y-%m-%d %H:%M")
					newpost.slug = fm['slug']
	            
	            	# Content
	            	# We regex replace {: .class #id } jekyll notation to:
	            	# { .class #id } WordPress notation
					newpost.content = re.sub(r"{:(.*)}",r"{\1}", fm.content)
	            	
					# Categories and tags
					if fm['tags']:
						tags = fm['tags'].split(",")
					else:
						tags = ''
				
					if fm['categories']:
						categories = fm['categories'].split(",")
					else:
						categories = ''
					
					newpost.terms_names = {
	            		'post_tag': tags,
	            		'category': categories,
	            	}
	            
					# Check to see if we have a linked post or regular post and set accordingly
					if fm['type'] == 'link':
						newpost.post_format = "Link"
						newpost.custom_fields = []
						newpost.custom_fields.append({'key': 'external-url','value': fm['external-url']})
	            
					# Make sure we set our post to "published"
					newpost.post_status = 'publish'
	            
					# Submit new post
					print("Publishing post to WordPress: %s" % fm['title'])
					wp.call(NewPost(newpost))
					
				elif fm['layout'] == 'page':
					
					# create new page from source content
					newpage = WordPressPage()
		            
					# Set the easy values
					newpage.title = fm['title']
					newpage.content = fm.content
	
					# Use page date if it exists
					if 'date' in fm.metadata:
						newpage.date = datetime.datetime.strptime(fm['date'], "%Y-%m-%d %H:%M")
	
					# Try to derive the permalink
					if fm['permalink']:
						permalink_raw = fm['permalink'].split("/")
						path_array = filter(None, permalink_raw)
						newpage.slug = path_array[-1]				
	
					# Make sure we set our post to "published"
					newpage.post_status = 'publish'
	
					# Submit new page
					print("Publishing page to WordPress: %s" % fm['title'])
					wp.call(NewPost(newpage))
					
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
			f = open('%s%s' % (path, file), 'w')
			f.write(output)
			f.close

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
		consumer_key="XXXXXXXXXXXX",
		consumer_secret="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
		api="wp-json",
		version='wp/v2',
		wp_user=args.username,
		wp_pass=passwd,
		basic_auth = True,
		user_auth = True,
	)
	
	#wp = WordpressJsonWrapper(args.site + '/wp-json/wp/v2', args.username, passwd)
	#wp = Client(args.site + '/xmlrpc.php', args.username, passwd)

	wp_export(args.folder)