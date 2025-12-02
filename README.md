To Run The Demo.

First you need to install everything in the reqiurments.txt file which includes:
elevenlabs
pyaudio
openai
dotenv
pillow
langchain_community

You can do a simple install by doing the command uv pip install -r requirements.txt. if this does not work then you can simply manually install by doing pip  install then the package name. 

Id recomended you setup the virtual enviroment by simply doing python -m venv venv which sets up a local virtual enviroment. 

Once you pull this repo you can then simply run the main.py file by doing python .\main.py to run the program. It should then start the chatbot and you should hear the chatbot speak. it already by default has microphone access due to pyaudio so permissions as of right now are set to alwasys on by defualt. 

You can ask it some questons but as of right now does not do much. To end the conversation simply say something that mentions that you want to end the converstaion and it should do it automatically. 
NOTE**
Make sure you have the virtual enviroment activated by running .\venv\Scripts\activate 

Basic ChatBot Calculation:
Trigger Words: calculate, compute, solve, find, equal, equals, what is, what's(may remove equal/equals in the future)
    : Used to let the bot know that it is asking for math work. Must be the first word in the sentence(NOTE: Prior it would interpret "what is" as a phrase for asking the current time, has been fixed)
Calcuation words: plus, minus, times, multiplied by, divided by, over, x(might take out): Chatbot looks for the word and replaces with the symbol. 
Additional calculation words(for more variety and the case of "and"): sum of, product of, difference of, quotient of
Examples: What is 3 times 3, Calculate 5 plus 4, Compute the quotient of 100 and 20, Solve 13 minus 9. 
Don't need to ask the Bot to do calculations, simply speak a math question and it will automatically do the problem

HOW TO BUILD APPLICATION
To build talk assist you must run the following command in the working directory. .\build_exe.bat this will build the application.

# added on december 1
now support online reminder and GUI TTS queue fixed
now you can set reminder using the online mode.
