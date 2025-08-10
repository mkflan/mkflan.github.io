+++
title = "Developing my Blog Website"
date = 2025-08-09
+++

I have always entertained the idea of creating a blog website, but I never followed through on it. After more recent thought, I realized how great of an idea it was: it helps me track my progress, reflect on projects, improve my writing and communication skills, and allows me to explain what I have learned to others which could help improve my own understanding.
# Planning
My vision for the site was simple. I wanted a modern and minimalist user interface, and to be able to have my Markdown files transformed into HTML. I did not want to go overkill on what frameworks and libraries I would use as I wanted to keep everything simple; I only wanted to use what was absolutely necessary for my goals; if I found later on that I wanted something that the current setup could not fulfill, I could expand then.

I settled with a static site generator named [**Zola**](https://www.getzola.org/). A **static site generator (SSG)** is software that builds websites (HTML and CSS) from, most frequently, Markdown files. This is exactly what I wanted! I could write my Markdown files, upload the Markdown file to the site, and have it rendered as an HTML page.
# Styling Challenges
This project marked my first true endeavor into frontend web development, and my most extensive journey into CSS thus far. As a note, I only styled the website for large screen devices; I might style it for smaller viewports in the future.
## The Header
The header consists of a singular `<h1>` and a `<nav>` element containing navigation links as anchors (`<a>`); I wanted to place the former to the left and the latter to the right. The solution to this was the **flexbox** layout method; flexbox is used to arrange items in one-dimension in either rows or columns. An element becomes a **flex container** when its `display` property is set to `flex`, which sets its inner display type[^1] and makes children elements **flex items** that adhere to the flexbox specification[^2]. Flex containers have a main axis along which flex items are laid out; its orientation is determined by the `flex-direction` property. By default, the main axis of a flex container is horizontal, positioning children in source order from left to right, which is what I wanted. The main axis starts at a point known as the **main start** and ends at a point known as the **main end**. The `justify-content` content property allows the developer to specify how flex items should be placed along the main axis. The `space-between` value was exactly what I was looking for: it evenly spaces items, in source code order, starting at the main start and ending at the main end. In my situation, this means that the left edge of the `h1`'s box would be at the main start and the right edge of `<nav>`'s box would be at the main end.

Now that the layout of the whole header was set, I turned my focus to the navigation section. The navigation anchors wrapped a singular `<h2>`. By default, the navigation anchors were stacked on top of each other; this was because `h2`'s default outer display type is `block`, which includes line breaks and overrides the behavior of anchor tags' default of `inline`. To solve this, I added a `display: inline-block` declaration in a `nav a` rule. `inline-block` acts as a compromise between `inline` and `block`: line breaks are not inserted and horizontal margins affect neighboring anchors.

My final challenge was making the header "stick" to the top of the page. To do this, I had to learn more about how elements are laid out in relation to one another. My preliminary exploration into the box model and the `display` property only explained how elements are laid out individually, in isolation. CSS has a `position`[^3] property, which allows you to escape the normal document flow and control how boxes are positioned in relation to other boxes. By default, every element has a `static` position, which puts them in their default positions in the normal document flow. Other options exist such as `relative`, which allows an element to be positioned relative to where it would normally be without affecting neighboring elements, and `fixed`, which keeps an element's position the same; exact positioning can be controlled using the `top`, `bottom`, `left`, and `right` properties. For my scenario, the `sticky` position was the first part of the solution: `sticky` allows elements to act as if it were positioned relatively until a certain point where its position becomes fixed. I also had to add a `top: 0` declaration, which kept the header at the top of its block. To control the stacking of elements in relation to each other, I had to set the `z-index` property. Elements with a higher `z-index` overlay those with a lower one if both elements are in the same **stacking context**. Since `header` and `main` are in the same stacking context, I just had to set `header`'s `z-index` to a value higher than `main`'s (which was 0). Even after all of this, the main page content still overlapped with the header! I was stumped. It turns out that I had to set the `background-color` property of the `header` element. Wow, how simple. The background of all elements is transparent by default, so that explained why the content would visibly overlap. Setting `background-color` would make the background opaque. After setting `background-color` to the same color as the page, everything work as desired!
## Laying out the page for posts
Perhaps the most important part was properly laying out the page for a post. I knew that I wanted to just include the post content and a table of contents on the right side. Laying these out proved a greater challenge than I initially thought. 

I split a post page into two `<div>`'s: one for the post content (class `content`) and one for the table of contents (class `toc`). I wanted the post content on the left and the table of contents on the right, with the content taking up a majority of the viewport width. I initially achieved the layout by making `<main>`, which was the parent of both of the divs, a flex container, but I found it challenging to fix the table of contents to the side of the viewport. The solution was to add a `display: inline-block` declaration for `.content` and `.toc`. But, I noticed that `.toc`'s box was going off of the viewport. This was happening because I gave `.content` left and right padding, which is not included in the actual dimensions of the box in the normal box model. The solution was using the alternative box model, `border-box`, which included padding in the actual dimensions of the box. This yielded the final rule of:
```css
.content, .toc {
	display: inline-block;
	box-sizing: border-box;
}
```

The next challenge was fixing `.toc` to the side of the screen. This was easy with my newfound knowledge of positioning: set its position to `fixed`.
## Maintaining Markdown styling
Zola uses Markdown files as a foundation for generating HTML. Markdown is a very useful, portable, and versatile format, allowing various styling options such as italicizing, bolding, code blocks, etc. When testing how Zola reflected the Markdown styling in the generated HTML, I realized that the generated pages were not styled properly. Thus, I had to manually style them. To figure out what tags Zola used for these styles, I had to manually build the site and inspect the generated files. I found that Zola wrapped italicized text in `<em>` tags, bolded text in `<strong>` tags, and code blocks in `<code>` tags. To apply the styles, I inserted the following rules:
```css
strong {
	font-weight: bold;
}

em {
	font-weight: italic;
}

code {
	background-color: black;
}
```

For text wrapped in single backticks in Markdown, I wanted to style them with slightly rounded corners, and some left and right padding. Zola would wrap this text in a `<code>` tag. For text wrapped in triple backticks in Markdown, which is used for multi-line code blocks, Zola would also wrap it in a `<code>` tag wrapped in a `<pre>` tag. I did not want to give these `<code>` tags wrapped in a `<pre>` the left and right padding as it would mess with the alignment in the multi-line code blocks. To style only for `<code>` tags who were not direct children of `<pre>` tags, I leveraged CSS's powerful selection capabilities[^4]: 
```css
code:not(pre > code) {
	padding: 0px 5px;
}
```

For some reason, Zola would generate HTML for multi-line code blocks that styled `<code>` with a black background, as you would expect, but would give `<pre>` tags a non-black background color via an inline style. Unfortunately, inline styles take precedence over those defined in external stylesheets (`.css` files). Luckily, CSS has a mechanism for indicating that a style should take priority in the cascade[^5]: the `!important` property. I just had to include this after I set the `background-color` property of `<pre>` tags:
```css
code, pre {
	background-color: black !important;
}
```

Next, I wanted to properly style footnotes. Zola would generate a `<footer>` tag with the class `footnotes` with an ordered list (`<ol>`) that contained the footnotes. By default, the font size was pretty large and links did not have underlines as I had globally set anchor tags (`<a>`) to have no underline. To alleviate this, I wrote the following rules:
```css
.footnotes ol li {
	font-size: 15px;
}

.footnotes ol li a {
	text-decoration: underline;
}
```

I also realized that when I say used the table of contents to redirect to a section of the page, the heading would be covered by the header. Luckily, there is a special CSS property to deal with this: `scroll-padding-top`. I applied this property to the whole document:
```css
:root {
	scroll-padding-top: 150px;
}
```
## Minor Problems
I wanted footnotes to contain backlinks to where they originated from. Zola's `bottom_footnotes` config variable inserts these backlinks, generating anchored arrows. But, these arrows would not properly display on the webpage. All I had to do was ensure UTF-8 was being used for the HTML document, so I had to add: `<meta charset="UTF-8">` inside of the HTML `<head>`.
# Deploying
I decided to deploy using GitHub Pages. I just had to setup a simple Actions workflow which built the Zola site and put the build artifacts onto the `gh-pages` branch:
```yaml
on: push
name: Build and deploy site onto GitHub Pages

jobs:
  build:
      runs-on: ubuntu-latest
      if: github.ref == 'refs/heads/master'
      steps:
        - name: checkout
          uses: actions/checkout@v4
        - name: build_and_deploy
          uses: shalzz/zola-deploy-action@master
          env:
              PAGES_BRANCH: gh-pages
              TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

On the first run, the deployment failed because `GITHUB_TOKEN`, an auto generated access token, did not have write privileges to the repository. I just had to go to the repository's **settings > actions > general** and check **read and write permissions** under **workflow permissions**. 
# Takeaways
Although simple, I am very proud about how this turned out. I have learned so much more about how CSS works, specifically how elements are laid out and what "cascading" (CSS stands for **cascading style sheets**) actually means in practice. Reading documentation and extracting applicable information is a skill all programmers need, and I have certainly improved that skill. I also found that I was trying to fit unnecessary things into the scope of the project just because I wanted to; in short, I realized the backend was unnecessary and redundant. Always keep things simple.

[^1]: The inner display type determines how children elements are laid out. Read more [here](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics/Box_model). 
[^2]: [This](https://css-tricks.com/snippets/css/a-guide-to-flexbox/) is the best reference I have found for flexbox. The [MDN web docs page](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Flexbox#the_flex_model) is also great. 
[^3]: Read more about positioning [here](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Positioning).
[^4]: Read more about CSS selectors [here](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_selectors).
[^5]: The cascade decides what styles take precedence when multiple are defined on an element. Read more [here](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_cascade/Cascade).
