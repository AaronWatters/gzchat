# gzchat
A command line graphical LLM chat interface that opens in the browser.

<img src="shot.png" width="300"/>

# Installation

To install the python module and the command line into your existing python 3 installation:

```
 pip install gzchat
```

# Running the command line

To choose canned models from the interface launch the the command line with no arguments:

```
 gzchat
```

To specify the model name and end point explicitly:

```bash
 gzchat --model deepseek-ai/DeepSeek-R6 --url http://workergpuamd4:8000/v1/chat/completions
```

# Development install

To install the module in development mode, clone the git repository and then run:

```bash
pip install -e .
```