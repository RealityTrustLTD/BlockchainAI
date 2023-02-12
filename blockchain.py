import discord
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import hashlib
import numpy as np
from keras.preprocessing.text import Tokenizer
import cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json

# Discord client
client = discord.Client()

# Firebase credentials and app initialization
cred = credentials.Certificate("YOURFIREBASESESSIONTOKENHERE.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://YOURFIREBASEAPPINFO.firebaseio.com/'
})

# Reference to the Firebase Realtime Database
ref = db.reference()

# Load the tokenizer from the database
tokenizer_data = ref.child("tokenizer").get()
if tokenizer_data is None:
    # Tokenize text
    tokenizer = Tokenizer(num_words=10000000001, filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n', lower=True, split=' ')
else:
    tokenizer = Tokenizer(num_words=10000000001)
    tokenizer.filters = '!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n'
    tokenizer.lower = True
    tokenizer.split = ' '
    tokenizer.word_index = json.loads(tokenizer_data)

# Create the genesis block
genesis_block = {
    "index": 0,
    "timestamp": "",
    "username": "",
    "content": "",
    "tokenized": [],
    "word_index": {},
    "previous_hash": "0"
}

# Calculate the SHA256 hash of the block data
def calculate_hash(block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

# Cache for messages
cache = []

@client.event
async def on_message(message):
    global cache
    # Anonymize the username
    username = hashlib.sha256(message.author.name.encode()).hexdigest()
    
    if message.author == client.user:
        return
    if message.content == "!mine" or len("".join([m["content"] for m in cache])) + len(message.content) >= 2048:
        # Tokenize the cached messages
        content = "\n".join([m["content"] for m in cache])
        tokenizer.fit_on_texts([content])
        tokenized = tokenizer.texts_to_sequences([content])[0] 
        # Get the current block index
        block_index = ref.child("blockchain").child("index").get()
        if block_index is None:
            block_index = 1
            previous_hash = "0"
        else:
            block_index += 1
            latest_block = ref.child("blockchain").child("latest_block").get()
            previous_block = ref.child("blockchain").child(latest_block).get()
            previous_hash = latest_block
        # Create a new block with the current message data
        block = {
            "index": block_index,
            "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "username": username,
            "content": content,
            "tokenized": tokenized,
            "word_index": tokenizer.word_index,
            "previous_hash": previous_hash
        }
        # Calculate the SHA256 hash of the block data
        block_hash = calculate_hash(block)
        # Generate a private key for the block hash
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=512,
            backend=default_backend()
        )
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        # Add the block to the blockchain
        ref.child("blockchain").child(block_hash).set(block)
        ref.child("blockchain").child("index").set(block_index)
        ref.child("blockchain").child("latest_block").set(block_hash)
        # Output information about the new block
        # Clear the cache and the set of participating users
        cache = []

        # Send the private key to the user who triggered the new block
        #await message.author.send("Here is your private key for the newly mined block:")
        #await message.author.send("DO NOT LOSE IT! **NOBODY** CAN HELP YOU GET IT BACK IF YOU LOSE IT.")
        #await message.author.send(private_key_pem.decode())
        #await message.author.send("```")
        print(f"Added block with hash {block_hash} and index {block_index}")
        print(f"Current count of tokenized words in the database: {len(tokenizer.word_index) + 1}")
        # Announce the information about the mined block in the channel
        await message.channel.send(f"Block #{block_index} with hash {block_hash} has been mined! "
                                   f"{len(tokenizer.word_index)} new words have been tokenized.")
    else:
        # Add the message to the cache
        cache.append({
            "timestamp": message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "username": username,
            "content": message.content
        })

client.run('PUT_YOUR_DISCORD_KEY_HERE')
