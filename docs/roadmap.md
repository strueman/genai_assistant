***Roadmap for basic Virtual Assistant***

1. Understand the problem statement
The problem is to create to develop the program to be highly modifiable, easy to expand and customisable. Designing the program to be UI independant to allow for easy integration of any UI be it web, mobile, desktop etc. 

2. Define the scope of the project
We will be using python as the programming language.
openAI for the LLM and for Text Embedding.
Langchain for the framework to connect the LLM and the Vector Database

##Initial features
A python program that can connect to any openai compatible LLM
The endpoint, api keys, settings like temperature, max_tokens, etc. will be from an easy to edit config file that will have an iterface for viewing and changing settings.
Keeping a database of chat history. 


##Later features:
create a mods and plugins architecture to allow for easy expansion and customisation.
Integration with other openAI compatible LLM.
RAG Integration, web search, internet access, file search, Scrape, index and store Documentation from websites for RAG.
Process saved chat histories to extract , categroise, index and store information in database for RAG.
web based UI for easy interaction.
web based admin interface to manage the database, configurations and load and manage mods and plugins