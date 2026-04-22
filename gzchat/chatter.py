

# derived from /mnt/home/gkrawezik/BENCHMARKS/Nemotron-3/interactive_llm.py 

import argparse
import json
import H5Gizmos as gz
import aiohttp
import asyncio
import markdown
import html

LLMs = dict(
    deepseek = dict(
        url = "http://workergpuamd4:8000/v1/chat/completions",
        model = "deepseek-ai/DeepSeek-R1",
    ),
    nemotron = dict(
        url = "http://workergpu172:8000/v1/chat/completions",
        model = "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
    )
)

InjectCSS = """
thead {
  background-color: #f0f0f0;
}

tbody {
  background-color: #ffffff;
}

tfoot {
  background-color: #e8e8e8;
}

td {
  border: 1px solid #ddd;
  padding: 8px;
}

th {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
  background-color: #e888e8;
}
"""

PROMPT = """You are a helpful assistant. Answer the question as best as you can. 
If you don't know the answer, say you don't know. If the question is not clear, ask for clarification. 
Return only a valid markdown as a response.  Use code fences for code examples.
"""

TOKEN_COUNT = 300  # number of tokens to generate
TEMPERATURE = 0.4  # temperature
TOP_P = 1  # top_p value
FREQUENCY = 0.5  # frequency penalty
PRESENCE = 0.5  # presence penalty

def init_messages():
    return [{"role": "system", "content": PROMPT}]

def add_user_message(messages, content):
    messages.append({"role": "user", "content": content})

def std_textbox_tag(text, rows=10, cols=80, readonly=True):
    readonly_attr = "readonly" if readonly else ""
    return f'<textarea rows="{rows}" cols="{cols}" {readonly_attr} style="width: 100%;">{html.escape(text)}</textarea>'

class LLMQuery:

    thoughts_splitter = '\n</think>\n'

    def __init__(self, messages, model_name, url):
        self.messages = messages
        self.model_name = model_name
        self.url = url
        self.json_response = None

    def first_choice(self):
        if self.json_response is None:
            raise Exception("No response yet")
        return self.json_response["choices"][0]["message"]["content"]
    
    def thoughts_and_response(self):
        if self.json_response is None:
            raise Exception("No response yet")
        choice = self.first_choice()
        if self.thoughts_splitter not in choice:
            return None
        [thoughts, response] = choice.rsplit(self.thoughts_splitter, 1)
        # html escape the thoughts.
        thoughts = html.escape(thoughts)
        return (thoughts, response)
    
    def response_message(self, include_thoughts=False):
        "The response to store in the message history"
        if self.json_response is None:
            raise Exception("No response yet")
        if include_thoughts:
            content = self.first_choice()
        else:
            tr = self.thoughts_and_response()
            if tr is not None:
                (thoughts, response) = tr
                content = response
            else:
                content = self.first_choice()
        return {"role": "assistant", "content": content}

    async def get_response(self):
        headers = {
        #    "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model_name,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "frequency_penalty": FREQUENCY,
            "presence_penalty": PRESENCE,
#            "max_tokens": TOKEN_COUNT,
            "messages" : self.messages,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=data) as resp:
                if resp.status != 200:
                    raise Exception(f"Request failed with status code {resp.status}")
                d = await resp.json()
                self.json_response = d
                return d
            
def main(argv=None):
    parser = argparse.ArgumentParser(description="LLM Discussion")
    # optional model string like "deepseek-ai/DeepSeek-R1"
    parser.add_argument("--model", type=str, help="LLM model to use")
    # optional URL string for the LLM API endpoint
    parser.add_argument("--url", type=str, help="LLM API endpoint URL")
    myLLMs = LLMs.copy()
    LLMname = None
    args = parser.parse_args(argv)
    # if model and url are provided, add them to the LLMs dict with the model name as the key
    if args.model and args.url:
        myLLMs[args.model] = dict(model=args.model, url=args.url)
        LLMname = args.model
        #p(f"Added custom LLM: {args.model} with URL {args.url}")
    discussion = LLMDiscussion(LLMs=myLLMs, LLMname=LLMname)
    gz.serve(discussion.run())

class LLMDiscussion:

    def __init__(self, LLMs=LLMs, messages=None, LLMname=None):
        self.LLMs = LLMs
        self.selectedLLM = LLMname
        self.messages = messages if messages is not None else init_messages()
        self.header = gz.Html("<h1>LLM Discussion</h1>")
        choices = ["(choose a model)"] + list(LLMs.keys())
        self.choices = gz.DropDownSelect(choices, on_click=self.on_model_change)
        self.dashboard = gz.Stack([
            self.header,
            self.choices,
        ])
        self.dashboard.embedded_css(InjectCSS)
        
    def on_model_change(self, choice):
        self.selectedLLM = choice
        #p(f"Selected LLM: {self.selectedLLM}")
        if self.selectedLLM not in self.LLMs:
            self.info.html("Please select a valid model.")
            return
        params = self.LLMs[self.selectedLLM]
        self.chat(params)

    def on_new_subject(self, *ignored):
        self.messages = init_messages()
        self.interactions.append(gz.Html("<hr><h2>New Discussion:</h2>"))
        self.dialog.attach_children(self.interactions)
        self.info.html("Ask %s anything" % repr(self.selectedLLM))
        self.scroll_to_bottom()

    def chat(self, params):
        self.text_area = gz.TextArea(rows=10, cols=80)
        self.button = gz.Button("Ask", on_click=self.on_ask)
        summarize_button = gz.Button("Summarize", on_click=self.on_summarize)
        new_subject_button = gz.Button("New Discussion", on_click=self.on_new_subject)
        header = gz.Html("<h1>Dialogue:</h1>")
        self.interactions = [header]
        self.dialog = gz.Stack(self.interactions)
        self.info = gz.Html(("<em>Ask %s anything</em>") % repr(self.selectedLLM))
        self.save_button = gz.Button("Save", on_click=self.on_save)
        self.filename_input = gz.Input("response_history.json")
        self.filename_visible = False
        self.filename_input.css({"display": "none"})
        self.all_buttons = [self.button, summarize_button, new_subject_button]
        query_div = gz.Stack([
            self.text_area, 
            [self.button, summarize_button, new_subject_button, self.filename_input, self.save_button]
            ])
        self.dashboard.attach_children([
            self.dialog,
            self.info,
            query_div,
        ])

    def on_save(self, *ignored):
        if not self.filename_visible:
            self.filename_input.css({"display": "inline-block"})
            self.filename_visible = True
            self.save_button.text("save history to file")
            return
        filename = self.filename_input.value.strip()
        if filename == "":
            self.info.html("<b>Please enter a valid filename to save the history.</b>")
            return
        # save the message history to a json file
        with open(filename, "w") as f:
            json.dump(self.messages, f, indent=2)
        self.info.html(f"<b>History saved to {filename}</b>")
        self.scroll_to_bottom()

    def enable_buttons(self, enabled=True):
        for button in self.all_buttons:
            button.set_enabled(enabled)

    def on_summarize(self, *ignored):
        self.enable_buttons(False)
        self.button.text("Summarizing...")
        gz.schedule_task(self.summarize())

    async def summarize(self):
        # summarize the conversation so far and replace the message history with the summary to save tokens
        summary_prompt = "Summarize this discussion so far."
        await self.ask_llm(summary_prompt)
        summary = self.messages[-1]["content"]
        #("summary", summary)
        self.messages = init_messages() + [{"role": "system", "content": "The following is a summary of the discussion so far: %s" % summary}]
        self.interactions.append(gz.Html("<hr><h2>Context Summarized</h2>"))
        self.dialog.attach_children(self.interactions)
        self.scroll_to_bottom()

    def on_ask(self, *ignored):
        user_input = self.text_area.value.strip()
        #p("user input", repr(user_input))
        self.enable_buttons(False)
        self.button.text("Asking...")
        self.info.html("Asking %s... %s" % (repr(self.selectedLLM), std_textbox_tag(user_input, rows=3, readonly=True)))
        self.text_area.set_value("")
        gz.schedule_task(self.ask_llm(user_input))

    async def ask_llm(self, user_input):
        try:
            add_user_message(self.messages, user_input)
            params = self.LLMs[self.selectedLLM]
            query = LLMQuery(self.messages, params["model"], params["url"])
            await query.get_response()
            response = query.first_choice()
            #p("response", repr(response))
            # get thoughts and response if available
            thoughts_and_response = query.thoughts_and_response()
            thoughts = None
            if thoughts_and_response is not None:
                (thoughts, response) = thoughts_and_response
            # add the response to the message history
            self.messages.append(query.response_message())
            # count newlines in user input
            user_input_newlines = user_input.count('\n')
            rows = max(3, user_input_newlines + 1)
            # format response markdown as html
            response = markdown.markdown(response, extensions=["fenced_code", "tables"])
            user_query = gz.Html("<blockquote><b>User:</b> %s</blockquote>" % std_textbox_tag(user_input, rows=rows, readonly=True))
            llm_response = gz.Html("<b>%s:</b> %s" % (repr(self.selectedLLM), response))
            # if there are thoughts, include them in the display with a show/hide toggle
            thoughts_div = None
            if thoughts is not None:
                thoughts_div = gz.Html("""
                                       <details><summary>LLM Thoughts</summary>
                                       <textarea readonly rows=10 cols=80 style="width: 100%%;">%s</textarea>
                                       </details>
                                       """ % thoughts)
                #self.interactions.append(thoughts_div)
            self.interactions.append(user_query)
            if thoughts_div is not None:
                self.interactions.append(thoughts_div)
            self.interactions.append(llm_response)
            self.dialog.attach_children(self.interactions)
            self.info.html("Ask %s anything" % repr(self.selectedLLM))
            self.scroll_to_bottom()
        except Exception as ex:
            #p("ask_llm exception", repr(ex))
            self.info.html(
                "<b>Error while asking %s:</b> <em>%s</em>"
                % (repr(self.selectedLLM), html.escape(str(ex)))
            )
            # reraise the exception to show it in the console
            raise ex
        finally:
            self.enable_buttons(True)
            self.button.text("Ask")

    def scroll_to_bottom(self):
        window = self.dashboard.window
        document = window.document
        # smooth scroll to bottom
        gz.do(
            window.scrollTo({
                "top": document.documentElement.scrollHeight,
                "behavior": "smooth"
            })
        )

    async def run(self):
        await self.dashboard.link()
        if self.selectedLLM is not None:
            params = self.LLMs[self.selectedLLM]
            self.chat(params)

if __name__ == "__main__":
    gz.serve(LLMDiscussion().run())
