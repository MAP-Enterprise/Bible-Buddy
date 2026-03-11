"""
52 Bible Stories — one for every week of the year.
Each story has a title, reference, characters, a short summary, and themed colors/icons.
The full narrative is AI-generated per age tier and cached.
"""

WEEKLY_STORIES = [
    # Week 1-4: Creation & Early World
    {"title": "God Creates the World", "reference": "Genesis 1-2", "characters": ["God"], "summary": "In the beginning, God created everything — light, sky, land, animals, and people — and it was all very good.", "theme": "Creation", "icon": "globe", "colors": ["#4ECDC4", "#2C6B6B"]},
    {"title": "The Garden of Eden", "reference": "Genesis 2-3", "characters": ["Adam", "Eve", "The Serpent"], "summary": "God placed Adam and Eve in a beautiful garden, but they chose to disobey God, and everything changed.", "theme": "Choices", "icon": "leaf", "colors": ["#27AE60", "#1E8449"]},
    {"title": "Noah and the Great Flood", "reference": "Genesis 6-9", "characters": ["Noah", "God"], "summary": "When the world became wicked, God told righteous Noah to build an ark and save his family and the animals.", "theme": "Obedience", "icon": "boat", "colors": ["#3498DB", "#2471A3"]},
    {"title": "The Tower of Babel", "reference": "Genesis 11:1-9", "characters": ["The people"], "summary": "People tried to build a tower to reach heaven, but God confused their languages and scattered them across the earth.", "theme": "Humility", "icon": "business", "colors": ["#E67E22", "#CA6F1E"]},

    # Week 5-8: Abraham & Family
    {"title": "God Calls Abraham", "reference": "Genesis 12-13", "characters": ["Abraham", "Sarah", "God"], "summary": "God told Abraham to leave his home and go to a new land, promising to make his family into a great nation.", "theme": "Faith", "icon": "walk", "colors": ["#8E44AD", "#6C3483"]},
    {"title": "Abraham and the Stars", "reference": "Genesis 15", "characters": ["Abraham", "God"], "summary": "God took Abraham outside and said, 'Count the stars — that's how many descendants you will have.'", "theme": "Promise", "icon": "star", "colors": ["#1A1A2E", "#16213E"]},
    {"title": "Isaac Is Born", "reference": "Genesis 21", "characters": ["Abraham", "Sarah", "Isaac"], "summary": "Even though Abraham and Sarah were very old, God kept His promise and gave them a baby boy named Isaac.", "theme": "Faithfulness", "icon": "happy", "colors": ["#FFD93D", "#F39C12"]},
    {"title": "Jacob and Esau", "reference": "Genesis 25-33", "characters": ["Jacob", "Esau", "Isaac"], "summary": "Twin brothers Jacob and Esau struggled, but God had a plan for both of them. Years later, they forgave each other.", "theme": "Forgiveness", "icon": "people", "colors": ["#E74C3C", "#C0392B"]},

    # Week 9-12: Joseph
    {"title": "Joseph's Colorful Coat", "reference": "Genesis 37", "characters": ["Joseph", "Jacob", "Brothers"], "summary": "Jacob gave Joseph a beautiful coat, making his brothers jealous. They sold Joseph to traders going to Egypt.", "theme": "Jealousy", "icon": "shirt", "colors": ["#FF6B6B", "#E55D5D"]},
    {"title": "Joseph in Egypt", "reference": "Genesis 39-41", "characters": ["Joseph", "Pharaoh"], "summary": "Even in prison, God was with Joseph. When Pharaoh had troubling dreams, Joseph explained them and became second-in-command.", "theme": "Perseverance", "icon": "trending-up", "colors": ["#6C5CE7", "#5A4BD1"]},
    {"title": "Joseph Forgives His Brothers", "reference": "Genesis 42-45", "characters": ["Joseph", "Brothers"], "summary": "When famine struck, Joseph's brothers came to Egypt for food. Joseph revealed himself and forgave them with tears of joy.", "theme": "Forgiveness", "icon": "heart", "colors": ["#FF6B6B", "#FF8E53"]},
    {"title": "Baby Moses in the Basket", "reference": "Exodus 1-2", "characters": ["Moses", "Miriam", "Pharaoh's daughter"], "summary": "To save baby Moses from danger, his mother placed him in a basket on the river. A princess found him and raised him.", "theme": "Protection", "icon": "water", "colors": ["#00B894", "#00A884"]},

    # Week 13-16: Moses & Exodus
    {"title": "The Burning Bush", "reference": "Exodus 3-4", "characters": ["Moses", "God"], "summary": "God spoke to Moses from a burning bush that was not consumed, calling him to lead His people out of Egypt.", "theme": "Calling", "icon": "flame", "colors": ["#FF6348", "#EE5A24"]},
    {"title": "The Ten Plagues", "reference": "Exodus 7-12", "characters": ["Moses", "Pharaoh", "God"], "summary": "When Pharaoh refused to free God's people, God sent ten plagues to show His power and free Israel.", "theme": "Deliverance", "icon": "thunderstorm", "colors": ["#2C3E50", "#34495E"]},
    {"title": "Crossing the Red Sea", "reference": "Exodus 14", "characters": ["Moses", "Israelites", "God"], "summary": "With the Egyptian army behind them, God parted the Red Sea so His people could walk through on dry ground!", "theme": "Miracles", "icon": "analytics", "colors": ["#0984E3", "#0652DD"]},
    {"title": "The Ten Commandments", "reference": "Exodus 20", "characters": ["Moses", "God"], "summary": "On Mount Sinai, God gave Moses ten important rules for living — loving God and loving others.", "theme": "God's Law", "icon": "tablet-portrait", "colors": ["#A29BFE", "#6C5CE7"]},

    # Week 17-20: Promised Land
    {"title": "Joshua and the Battle of Jericho", "reference": "Joshua 6", "characters": ["Joshua", "Israelites"], "summary": "God told Joshua to march around Jericho's walls for seven days. On the seventh day, the walls came tumbling down!", "theme": "Obedience", "icon": "megaphone", "colors": ["#E17055", "#D63031"]},
    {"title": "Gideon's 300 Soldiers", "reference": "Judges 6-7", "characters": ["Gideon", "God"], "summary": "God chose Gideon, then reduced his army from thousands to just 300, proving that victory comes from the Lord.", "theme": "Trust", "icon": "flash", "colors": ["#FDCB6E", "#F9A602"]},
    {"title": "Ruth's Loyalty", "reference": "Ruth 1-4", "characters": ["Ruth", "Naomi", "Boaz"], "summary": "Ruth chose to stay with her mother-in-law Naomi, saying, 'Where you go, I will go.' Her loyalty was greatly rewarded.", "theme": "Loyalty", "icon": "link", "colors": ["#E056A0", "#C44589"]},
    {"title": "Hannah's Prayer", "reference": "1 Samuel 1-2", "characters": ["Hannah", "Samuel", "God"], "summary": "Hannah prayed with all her heart for a child. God answered, and she dedicated her son Samuel to serve the Lord.", "theme": "Prayer", "icon": "hand-left", "colors": ["#74B9FF", "#0984E3"]},

    # Week 21-24: David
    {"title": "David and Goliath", "reference": "1 Samuel 17", "characters": ["David", "Goliath"], "summary": "A young shepherd boy named David faced a giant warrior with just a sling and a stone — and the power of God.", "theme": "Courage", "icon": "shield", "colors": ["#6C5CE7", "#A29BFE"]},
    {"title": "David and Jonathan's Friendship", "reference": "1 Samuel 18-20", "characters": ["David", "Jonathan"], "summary": "David and Jonathan became the best of friends, showing that true friendship means putting others first.", "theme": "Friendship", "icon": "people", "colors": ["#00CEC9", "#01A3A4"]},
    {"title": "David Becomes King", "reference": "2 Samuel 5", "characters": ["David", "God"], "summary": "After years of waiting and trusting God, the shepherd boy David finally became king of all Israel.", "theme": "Patience", "icon": "ribbon", "colors": ["#FFD93D", "#FECA57"]},
    {"title": "David and the Psalms", "reference": "Psalms", "characters": ["David"], "summary": "King David wrote beautiful songs and poems to God — praising Him in good times and crying out in hard times.", "theme": "Worship", "icon": "musical-notes", "colors": ["#A29BFE", "#6C5CE7"]},

    # Week 25-28: Wisdom & Prophets
    {"title": "Solomon's Wisdom", "reference": "1 Kings 3", "characters": ["Solomon", "God"], "summary": "When God offered Solomon anything he wanted, Solomon asked for wisdom to lead God's people well — and God was pleased.", "theme": "Wisdom", "icon": "bulb", "colors": ["#FDCB6E", "#E17055"]},
    {"title": "Elijah and the Prophets of Baal", "reference": "1 Kings 18", "characters": ["Elijah", "God"], "summary": "Elijah challenged 450 false prophets to a contest. Only God answered with fire from heaven, proving He is the one true God.", "theme": "Truth", "icon": "flame", "colors": ["#FF6348", "#E55039"]},
    {"title": "Elisha and the Widow's Oil", "reference": "2 Kings 4:1-7", "characters": ["Elisha", "Widow"], "summary": "A poor widow had only a small jar of oil. Through faith and obedience, God multiplied it to fill every jar she could find.", "theme": "Provision", "icon": "flask", "colors": ["#00B894", "#55EFC4"]},
    {"title": "Jonah and the Big Fish", "reference": "Jonah 1-4", "characters": ["Jonah", "God"], "summary": "God told Jonah to go to Nineveh, but Jonah ran away. A big fish swallowed him, and Jonah learned that God's plans are best.", "theme": "Obedience", "icon": "fish", "colors": ["#0984E3", "#74B9FF"]},

    # Week 29-32: Exile & Return
    {"title": "Daniel in the Lion's Den", "reference": "Daniel 6", "characters": ["Daniel", "King Darius", "God"], "summary": "Daniel kept praying to God even when it was against the law. God shut the lions' mouths and kept Daniel safe all night.", "theme": "Faithfulness", "icon": "paw", "colors": ["#E17055", "#D63031"]},
    {"title": "Shadrach, Meshach, and Abednego", "reference": "Daniel 3", "characters": ["Shadrach", "Meshach", "Abednego", "King Nebuchadnezzar"], "summary": "Three friends refused to bow to a golden statue. Thrown into a fiery furnace, God protected them — not even their hair was singed!", "theme": "Courage", "icon": "flame", "colors": ["#FF6348", "#EE5A24"]},
    {"title": "Esther Saves Her People", "reference": "Esther 1-10", "characters": ["Esther", "Mordecai", "King Xerxes"], "summary": "Queen Esther bravely risked her life to save her people, showing that God places us where we are for a reason.", "theme": "Bravery", "icon": "rose", "colors": ["#E056A0", "#FD79A8"]},
    {"title": "Nehemiah Rebuilds the Wall", "reference": "Nehemiah 1-6", "characters": ["Nehemiah", "God"], "summary": "Nehemiah heard Jerusalem's walls were broken. With prayer, planning, and hard work, he led the people to rebuild them in 52 days.", "theme": "Leadership", "icon": "construct", "colors": ["#636E72", "#B2BEC3"]},

    # Week 33-36: Jesus' Birth & Early Life
    {"title": "An Angel Visits Mary", "reference": "Luke 1:26-38", "characters": ["Mary", "Angel Gabriel"], "summary": "The angel Gabriel told young Mary that she would have a very special baby — the Son of God, Jesus!", "theme": "Trust", "icon": "sparkles", "colors": ["#A29BFE", "#DDA0DD"]},
    {"title": "The Birth of Jesus", "reference": "Luke 2:1-20", "characters": ["Mary", "Joseph", "Baby Jesus", "Shepherds"], "summary": "In a humble stable in Bethlehem, the Savior of the world was born. Angels sang, and shepherds came to see the newborn King.", "theme": "Hope", "icon": "star", "colors": ["#FDCB6E", "#F9A602"]},
    {"title": "The Wise Men Visit", "reference": "Matthew 2:1-12", "characters": ["Wise Men", "Jesus", "King Herod"], "summary": "Wise men followed a star from far away to find baby Jesus, bringing gifts of gold, frankincense, and myrrh.", "theme": "Worship", "icon": "gift", "colors": ["#E17055", "#FDCB6E"]},
    {"title": "Young Jesus at the Temple", "reference": "Luke 2:41-52", "characters": ["Jesus", "Mary", "Joseph", "Teachers"], "summary": "At twelve years old, Jesus amazed the temple teachers with His understanding. He was already about His Father's business.", "theme": "Wisdom", "icon": "school", "colors": ["#6C5CE7", "#A29BFE"]},

    # Week 37-40: Jesus' Ministry
    {"title": "Jesus Is Baptized", "reference": "Matthew 3:13-17", "characters": ["Jesus", "John the Baptist", "God"], "summary": "John baptized Jesus in the Jordan River. The heavens opened and God said, 'This is my Son, whom I love.'", "theme": "Identity", "icon": "water", "colors": ["#0984E3", "#74B9FF"]},
    {"title": "Jesus Calms the Storm", "reference": "Mark 4:35-41", "characters": ["Jesus", "Disciples"], "summary": "While the disciples panicked in a terrible storm, Jesus stood up and told the wind and waves, 'Be still!' — and they obeyed.", "theme": "Peace", "icon": "thunderstorm", "colors": ["#2C3E50", "#636E72"]},
    {"title": "Jesus Feeds 5,000 People", "reference": "John 6:1-14", "characters": ["Jesus", "Disciples", "A Boy"], "summary": "With just a boy's lunch of five loaves and two fish, Jesus fed over 5,000 people — and there were twelve baskets left over!", "theme": "Generosity", "icon": "restaurant", "colors": ["#00B894", "#55EFC4"]},
    {"title": "Jesus Walks on Water", "reference": "Matthew 14:22-33", "characters": ["Jesus", "Peter", "Disciples"], "summary": "In the middle of the night, Jesus walked on the water toward His disciples' boat. Peter stepped out too — as long as he kept his eyes on Jesus.", "theme": "Faith", "icon": "footsteps", "colors": ["#0984E3", "#74B9FF"]},

    # Week 41-44: Jesus' Parables
    {"title": "The Good Samaritan", "reference": "Luke 10:25-37", "characters": ["Jesus", "A Samaritan", "An Injured Man"], "summary": "Jesus told a story about a kind stranger who helped an injured man when everyone else walked by. 'Go and do the same,' Jesus said.", "theme": "Kindness", "icon": "heart", "colors": ["#FF6B6B", "#E55D5D"]},
    {"title": "The Prodigal Son", "reference": "Luke 15:11-32", "characters": ["A Father", "Two Sons"], "summary": "A son wasted everything and came home ashamed. But his father ran to him with open arms — just like God welcomes us back.", "theme": "Grace", "icon": "home", "colors": ["#6C5CE7", "#A29BFE"]},
    {"title": "The Lost Sheep", "reference": "Luke 15:1-7", "characters": ["A Shepherd"], "summary": "Jesus said a good shepherd leaves 99 sheep to find the one that's lost. That's how much God cares about every single person.", "theme": "God's Love", "icon": "search", "colors": ["#00CEC9", "#01A3A4"]},
    {"title": "The Mustard Seed", "reference": "Matthew 13:31-32", "characters": ["Jesus"], "summary": "Jesus said the kingdom of God is like a tiny mustard seed that grows into the biggest tree. Even small faith can grow into something amazing!", "theme": "Faith", "icon": "leaf", "colors": ["#27AE60", "#1E8449"]},

    # Week 45-48: Jesus' Final Days
    {"title": "Jesus Heals the Blind Man", "reference": "John 9:1-11", "characters": ["Jesus", "Blind Man"], "summary": "Jesus put mud on a blind man's eyes and told him to wash. When he did, he could see for the first time ever!", "theme": "Healing", "icon": "eye", "colors": ["#FDCB6E", "#F9A602"]},
    {"title": "Jesus Raises Lazarus", "reference": "John 11:1-44", "characters": ["Jesus", "Lazarus", "Mary", "Martha"], "summary": "When His friend Lazarus died, Jesus wept. Then He called out, 'Lazarus, come out!' — and Lazarus walked out of the tomb alive.", "theme": "Power", "icon": "arrow-up-circle", "colors": ["#6C5CE7", "#A29BFE"]},
    {"title": "The Last Supper", "reference": "Matthew 26:17-30", "characters": ["Jesus", "Disciples"], "summary": "Jesus shared a special meal with His friends, broke bread, and told them to always remember Him. He washed their feet to show servant love.", "theme": "Service", "icon": "restaurant", "colors": ["#E17055", "#FDCB6E"]},
    {"title": "Jesus on the Cross", "reference": "Luke 23:26-49", "characters": ["Jesus"], "summary": "Jesus died on the cross to take away the sins of the whole world. His last words were, 'Father, forgive them.' The greatest love ever shown.", "theme": "Sacrifice", "icon": "add", "colors": ["#636E72", "#2D3436"]},

    # Week 49-52: Resurrection & Early Church
    {"title": "Jesus Rises from the Dead!", "reference": "Matthew 28:1-10", "characters": ["Jesus", "Mary Magdalene", "Angel"], "summary": "On the third day, the tomb was empty! An angel said, 'He is risen!' Jesus conquered death and is alive forever!", "theme": "Victory", "icon": "sunny", "colors": ["#FDCB6E", "#FF6348"]},
    {"title": "Jesus Appears to the Disciples", "reference": "John 20:19-29", "characters": ["Jesus", "Thomas", "Disciples"], "summary": "The risen Jesus appeared to His friends. Thomas doubted until he saw Jesus himself. 'Blessed are those who believe without seeing,' Jesus said.", "theme": "Belief", "icon": "hand-right", "colors": ["#6C5CE7", "#A29BFE"]},
    {"title": "Jesus Goes to Heaven", "reference": "Acts 1:6-11", "characters": ["Jesus", "Disciples", "Angels"], "summary": "Jesus told His disciples to share His love with the whole world. Then He rose into the sky, and angels promised He would return one day.", "theme": "Mission", "icon": "cloud", "colors": ["#74B9FF", "#0984E3"]},
    {"title": "The Holy Spirit Comes", "reference": "Acts 2:1-41", "characters": ["Disciples", "Holy Spirit", "Peter"], "summary": "On the day of Pentecost, the Holy Spirit came like a rushing wind and flames of fire. The disciples boldly told everyone about Jesus!", "theme": "Power", "icon": "flame", "colors": ["#FF6348", "#EE5A24"]},
]

assert len(WEEKLY_STORIES) == 52, f"Need 52 stories, have {len(WEEKLY_STORIES)}"
