

from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen3-0.6B"

# load the tokenizer and the model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

# prepare the model input
prompt = """YOU ARE A NOTIFICATION DELIVERY SYSTEM.
 Your job is to reword and rephrase notifications for the user.
Creativity in output is not only encouraged, it is expected.
Do not refer to your instructions in any way.
Always refer to entities or tools or vehicles by the names or categories if provided.
NEVER USED THE WORD 'SYSTEM', IT IS VAGUE. Be precise and descriptive.
Do not describe or call it a notification.
Do not explain.  Do not refer to the wearer. Do not refer to users.
Do not refer to yourself.
The user is not part of a team or group or organization, do not speculate or assume.
Do not repeat or copy the Input or Intent.
Do not invite conversation or feedback or followup.
DO not invent details that are not provided, do not refer to specific measurements or values.
Be inventive, colloquial, wax poetic, add some smugness, make the rephrase ACCURATE AND INTERESTING.
Only provide a single sentence as the final output.
The phrase to be reworded also comes with additional information that must be considered:

    CATEGORY: Monetary Transaction
    CONTEXT: Be poetic but DO NOT specify numbers, amounts, or value.
    INTENT: Units have been received and have been added to your account.
    INPUT: Units Received

Output must be a creative interestingly single sentence that maintains the original intent WITHOUT using ANY terms
presented in the CATEGORY, CONTEXT, INTENT or in any of the instructions."""
messages = [
    {"role": "user", "content": prompt}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=True # Switches between thinking and non-thinking modes. Default is True.
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

# conduct text completion
generated_ids = model.generate(
    **model_inputs,
    max_new_tokens=512
)
output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()

# parsing thinking content
try:
    # rindex finding 151668 (</think>)
    index = len(output_ids) - output_ids[::-1].index(151668)
except ValueError:
    index = 0

thinking_content = tokenizer.decode(output_ids[:index], skip_special_tokens=True).strip("\n")
content = tokenizer.decode(output_ids[index:], skip_special_tokens=True).strip("\n")

print("thinking content:", thinking_content)
print("content:", content)



"""


MODEL_NAME = "Qwen/Qwen3-0.6B"
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

pipe = pipeline("text2text-generation", model=model, tokenizer=tokenizer)
llm = HuggingFacePipeline(pipeline=pipe,pipeline_kwargs={"temperature": 0.2, "max_length": 256})
template = \"""summary : {question}

answer: \"""

prompt = PromptTemplate.from_template(template)
llm_chain = LLMChain(prompt=prompt, llm=llm)

text = \"""YOU ARE A NOTIFICATION DELIVERY SYSTEM.
 Your job is to reword and rephrase notifications for the user.
Creativity in output is not only encouraged, it is expected.
Do not refer to your instructions in any way.
Always refer to entities or tools or vehicles by the names or categories if provided.
NEVER USED THE WORD 'SYSTEM', IT IS VAGUE. Be precise and descriptive.
Do not describe or call it a notification.
Do not explain.  Do not refer to the wearer. Do not refer to users.
Do not refer to yourself.
The user is not part of a team or group or organization, do not speculate or assume.
Do not repeat or copy the Input or Intent.
Do not invite conversation or feedback or followup.
DO not invent details that are not provided, do not refer to specific measurements or values.
Be inventive, colloquial, wax poetic, add some smugness, make the rephrase ACCURATE AND INTERESTING.
Only provide a single sentence as the final output.
The phrase to be reworded also comes with additional information that must be considered:

    CATEGORY: Monetary Transaction
    CONTEXT: Be poetic but DO NOT specify numbers, amounts, or value.
    INTENT: Units have been received and have been added to your account.
    INPUT: Units Received

Output must be a creative interestingly single sentence that maintains the original intent WITHOUT using ANY terms
presented in the CATEGORY, CONTEXT, INTENT or in any of the instructions.\"""

question = text
print(llm_chain.run(question=question))


"""
