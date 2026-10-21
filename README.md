# version v1


- In this version i created assign.py. 
- In v0, i used kmeans clustering to group items into 8 buckets, essentially it was pretty perfect at sorting by clothing type, i had a buckets of pants, sweatshirts, and accessories, and t-shirts. 
- I thought it would be useful to keep this, and then add a second layers of grouping by style. For this, I used CLIP again but for text matching. I created another 8 buckets for different 'aesthetics' described in text. 


- This actually worked quite well, but it uncovered that what i was building wasn't a reccomendation system as much as it was a search system. Honestly, it's a pretty good one, considering the first CLIP run doesn't consider any of the clothing data other than the image. 

#### Next Steps

- I think that the next steps will be to go high lever get more information out of each image, and then we can go back to traditional machine learning with that data. For example, I used an llm to create the names for each style bucket. I think that a quick llm call for each piece of clothing can be used in order to output text describing clothes that would be a good reccomendation candidate. 


so in summary atm:
- llm call for 'liked' products to find good accompanying products
- another clip call to take the output llm text and search for a piece like that.
