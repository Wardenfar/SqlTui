# SqlTui : All your sql servers in one tool

 - **FullScreen app**
 - Support for : **Mysql**, **PostgreSQL**
 - **Fully Configurable**
 - You can **add support** for a driver **easily**
 - **No Shortcuts to remember** : all possible bindings are in the bottom toolbar

## Installation

```shell
git clone ...
cd SqlTui/
pip3 install -r requirements.txt

# Add your Sql Server
nano config/servers.toml

# Run the tool
python3 main.py
```

## Server Configuration

To add or remove a server, edit `config/servers.toml`:

```toml
[servers]

[servers.server1]
driver = 'mysql' # or psql
user = 'admin'
password = 'admin'
host = 'localhost'
port = '3306'

# ...
```

## Configure the Drivers

To add an action, edit `config/drivers/[name].toml`:

There are two type of placeholder:
 - `#{database:id}` : replaced by the name of the node of this type and escaped as identifier (first result of the children_query) and escaped as an indentifier
 - `${Where Clause}` : ask the value to the user, the value will not be escaped

There are two type of escapes:
 - `':id'` : identifier
 - `':text'` : text
 - `''` : not escaped

Each node is defined like this :

```toml
[mysql.node.database] # [driver].node.[name]
color = "#ffff00" # node color
children_query = ["database", "SHOW TABLES;"] # connection_type, query
children_type = "table" # children node type
actions = [
    # Action Name, connection_type, query
    ["Drop", "database", "DROP DATABASE #{database:id};"]
]
extra_children = [ # extra children (buttons)
    # Button Name, color, connection_type, query
    ["<Add Table>", "white", "database", "CREATE TABLE ${Table name:id} (${Columns defintion});"]
]
open = ["database", ""] # Open connection tab : [connection_type], [default text] 
```