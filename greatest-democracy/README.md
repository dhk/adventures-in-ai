# Is the US The Greatest Democracy in the World?
## Project Summary
- Status: Exploring
- Problem: Compare how different democracy metrics change rankings
- Why AI: Accelerate data wrangling and exploratory analysis
- Artifacts: Notebooks, analysis summaries, prompts

This is a tongue-in-cheek analysis comparing 8 nations, each a democracy comparable to the USA.

The idea is to see how each nation scores compared to the USA.

The motivation for this was twofold:
* a line from a recent political speech
* my desire to see how well Claude/Colab/GitHub would play together

## Summary
* [the answers that Claude came up with](democracy-metrics-analysis-summary.md)
* the [Claude conversation log](user-instructions-summary.md), i.e., what I typed to get the results
* various `*.ipynb` files - the code that Claude generated for a Colab notebook
## Disclaimers
1. there's no verification of input data
2. enjoy at your own risk
3. MIT license for you to take and adapt as you see fit.
4. the weighting algorithms are truly scary.

## Observations & Notes
1. Claude does a good job of generating very journeyman code
1. Whenever you're looking at an analysis that claims to be weighted or representative of a population, make sure you understand the basis of that weighting.
1. Bias is everywhere (lol)
1. there's a non-trivial use case here: gather some real world data and fashion it for me
1. Not having to do the labor of assembling the code makes it way faster for me to iterate on my ideas. This is very much what EDA tools like Tableau espouse
1. reams of bar charts is just a bad idea. Get things in one place
1. avoid overloading stats by not normalizing


## To-Dos
- [ ] Convert the code to ordinary Python + pandas; add commits to track evolution
- [ ] Add in the section about why those countries were chosen as democracies
- [ ] Add Ireland, since I can't be parochial about NZ (the land of my birth) if I'm not parochial about Ireland (the land of my parents)

## Do you have feedback?
Want to argue with me or discuss this? Sure. https://tidycal.com/davehk/30-minute-coffee