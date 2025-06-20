+++
title = "Developing my Blog Website"
date = "2025-06-17"
+++

Creating a blog website has always been an idea of mine, but I never followed through on it. I have not historically written writeups on my projects or documented my computer science journey, but that idea sounds great to me; it allows me to see how I have progressed and also provides me an avenue to explain what I have learned to others which could hopefully improve my own understanding.
# Planning
My vision for the site was simple. I wanted: a modern and minimalist user interface, the ability to upload blog posts as Markdown files and have them rendered in the HTML, and to generate a table of contents using the Markdown headings. Sounds relatively simple.

I did not want to go overkill on what I used as a framework as I wanted to keep everything simple; I only wanted to use what was absolutely necessary for my goals. I ended up settling with a static site generator named Zola.

A **static site generator (SSG)** 

This would not be enough, though, to implement everything I wanted. Being solely a SSG, Zola is unable to handle uploading files through an endpoint. Thus, I needed a simple backend that could put Markdown files into their proper location and rebuild the site.
