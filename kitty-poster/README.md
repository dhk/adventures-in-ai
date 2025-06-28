## About Kitty-Poster
Goal of the project is to post three random kitty pix to Instagram each day.

My friends on Insta & Facebook really like those photos. And, I had a 3-year run of doing this manually. It always occurred to me that I should do it automatically. 

Now, with "Vibe Coding" and GenAI and all the rest, I thought it would be interesting to do it step-by-step.

Expert recommendations (including my own!) are to 
* describe the project in steps, and help the tools understand context
* Commit early/commit often - easier to roll back bad code from the LLMs.

Let's pause a moment.

"Commit" - that's not what Vibe Coding is all about? How is that end-user coding? 

Well, it's not. 

I've been vibe-coding for more than a year now -- before it had a name. Here's how I think about using GenAI tools to build apps

* If you have a single, well defined idea of limited complexity, then you'll probably have an excellent experience with the current version (June, 2025) of tools
* If you have complex needs, then you need to have a good understanding of software development practices. 

The complexities that I've discovered include:
* use of an external program or service: for example, what if you wanted to build an application that stored data into a database
* multiple service dependencies
* deployment of your app to the web or internet.


With that in mind, I'm going to scope the project into different stages:

1. Post three kitty images to Instagram, by running the program
2. Post three kitty images (3KIs) randomly chosen from a folder "without replacement".  By that I mean that once a kitty image is chosen, it won't be chosen again
3. Automate the posting of 3KIs
4. Create a way to easily upload KIs to this folder
5. Create a way for other people to contribute KIs
6. Verify that the KIs in the folder are actually kittens and not \<something else\>. Knowing and loving my friends as I do, I have to have a lot of strong defenses against, shall we say, non-kitty images. (NKIs)
7. Figre out how to track usage and engagement

That's it for now.

So, as I go through each phase of this project, I'll vibe-code \<sigh\> as much of this as possible, and call out where it was hard to get it right. 

I'm doing this to 
* demystify "vibe-coding" \<sigh\>; 
* practice building in a codespace
* get experience with github hooks and google cloud integrations.


Before I start: I need to have an idea of how I'm going to hook it all together. This is one of the things that is missed in much of the literature: the architecture that supports the product. 

Assuredly, the architecture will change as I discover stuff. 

But, without a plan we're nowhere. 

