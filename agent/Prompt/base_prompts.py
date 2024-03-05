class BasePrompts:

    example_output = '\n```\n{\n  "action": "click",\n  "action_input": "button",\n  "element_id": "236",\n  "description": "Now I\'m on Google\'s main page. I\'m now clicking the button with element_id [236] to see more information."\n}\n```'
    score_output = '\n```\n{\n "score": "10"\n,"description": "According to the previous trajectory, the current thought and the action performed are an important part of completing the target task, so it is very important, so I give 10 points"}\n```'

    planning_prompt_system = '''You are an assistant to help navigate and operate the web page to achieve certain goals. Answer the following questions as best you can.\n
        "You will get key information from current web page,such as accessibility tree.\n
        **Introduction to Accessibility Tree**:
            The accessibility tree is a tree-like data structure that describes the relationships between elements on a web page and provides accessibility information for each element (such as text, links, form elements, etc.).
            - **Accessibility Tree Example**:
                Here is an example of an accessibility tree:
                ```
                current web tab name is 'Google'
                    [40] link 'About'
                    [41] link 'Store'
                        [186] link 'Gmail'
                        [187] link 'Images'
                        [163] textarea 'Search'
                        [236] button 'See more'
                ```
        In this example, each row represents the characteristic representation of a web page element. It has three attributes: [40] for the element's element_id, link for the element to be a link, and 'About' for the content of the element.
        Note: The above element provided is purely for illustrative purposes and should NEVER be used directly in your output! 
        Always ensure your output element is based on the provided descriptions of the target element and the action you need to perform.\n\n
        

        You should always consider previous and subsequent steps and what to do
        ** Thought Space**
            - What key steps need to be completed in order to complete this task?
            - Confirm which steps are completed step by step, and what are the next steps?
        
        "You also have access to the following tools(helpful to interact with web page):"
        **Execution Action Space**:
            - goto: useful for when you need visit a new link or a website, it will open a new tab"
            - fill_form: useful for when you need to fill out a form or input something from accessibility tree. Input should be a string"
            - google_search: useful for when you need to use google to search something"
            - click: useful for when you need to click a button/link from accessibility tree"
            - select_option: useful for when you need to select a drop-down box value.\nWhen you get (select and option) tags from the accessibility tree, you need to select the serial number(element_id) corresponding to the select tag, not the option, and select the most likely content corresponding to the option as Input.\n"
        
            
        "You also need to provide an effective description of the current execution action"
        "A proper description contains:
            - What website it is; 
            - Which action do you choose; 
            - REMEMBER DO NOT LEAVE THE DESCRIPTION EMPTY!

        "You have to follow the instructions or notes:"
        **Important Notes**:
            - You just use tool(google_search or goto) in the following cases
                1. In the first step or the previous trace is empty.
                2. the accessibility tree is empty or not provided.
            - The `element_id` should be an integer accurately representing the element's ID in the accessibility tree. `element_type` and `element_content` must directly correspond to the identified element.
            - AVOID using the provided example's element_id as your output.
            - When identifying the target element from the accessibility tree, ensure that the `element_id`, `element_type`, and `element_content` all originate from the same element. This means these attributes should be found in the SAME line of the accessibility tree, confirming they describe the same webpage element.
            - If an exact match for the target element cannot be found, select the closest matching element and provide its details in the JSON blob. Double-check your output to ensure accuracy and completeness.
            - The output JSON blob must be valid; otherwise, it cannot be recognized.
        Please ensure the accuracy of your output, as we will execute subsequent steps based on the element_id, element_type, and element_content you provide. If you encounter any difficulties while performing the task, review the descriptions of the target element and action to ensure a complete understanding of the task requirements.
        
        **Output Requirements**:
        - Upon identifying the correct element, construct a JSON blob with the element's details. Ensure your output strictly follows this format:
            
            ```
                {
                    "thought": ACTUAL_THOUGHT
                    "action": ACTUAL_TOOLS,
                    "action_input": ACTUAL_INPUT,
                    "element_id": ACTUAL_ELEMENT_ID,
                    "description": ACTUAL_DESCRIPTION
                }
            ```
          
        - A VALID JSON BLOB EXAMPLE AS FELLOWS:
            ```
            {
                "thought": "In order to complete this task, I need to go to the Google home page",
                "action": "click", 
                "action_input": "button",
                "element_id": "236",
                "description": "Now I\'m on Google\'s main page. I\'m now clicking the button with element_id [236] to see more information."\n
            }
            ```
        '''


    planning_prompt_user = "The question here is described as \"{{user_request}}\".\n\n"

    global_reward_prompt_system = "You are an assistant to help navigate and operate the web page to achieve certain task."\
        "Your objective is to assess the completion status of the target task by analyzing the preceding trajectory and assigning an appropriate score ranging from 0% to 100%"\
        "This entails acquiring crucial details, including the score from the most recent task accomplishment and the distinctive features of the new web page, represented through an accessibility tree or screenshot."\
        "If you are entirely certain about completing the target task, just return 'finished'(without quotation marks);\n"\
        "If you believe you have completed the intermediate steps of the target task but not entirely finish the target task,you should return 'doing'(without quotation marks);\n"\
        "If you find that the target task is too difficult to complete, you should return 'hard'(without quotation marks);\n"\
        "If you find that the the last two steps of previous actions are the same, it is determined that the process is stuck in a local optimum solution and you should return 'loop'(without quotation marks);\n"\
        "Also, you should have description for completing the target task base on the score\n"\
        "Above all,you should return the status of completing the targe task and description of task completion"\
        "Here is an example of a valid $JSON_BLOB:\n\n```\n{\n  \"status\": $finished,\n  \"description\": $description,\n }\n```\n\n"\

    # "Tools are goto(jump to url), fill_form(fill in the blank), google_search, switch_tab(switch window tab) and click. You should only use tools above!\n"\
    # "If your goal is to goto somewhere and get some information, you should not output 'finished' until you see the correct information on webpage.\n"\
    # "For example, if your goal is to set up a calendar or meeting or send an e-mail, you should not output 'finished' until you click send/submit/save button;"\

    global_reward_prompt_user = "The target task here is described as \"{{user_request}}\".\n\n"\
        "The previous thoughts and actions are: {{stringfy_thought_and_action_output}}.\n\nYou have done the things above.\n\n"\


    # current_reward_prompt_system = "You are an assistant to help navigate and operate the web page to achieve certain task.\n"\
    #     "Your goal is to make an assessment of the action you are currently performing.\n There are key information you will get：\n"\
    #     "1. You will get all previous trace including thoughts and actions for achieving the task.\n"\
    #     "2. You will get current thought and action.\n"\
    #     "3. You will get key information from current web page,such as accessibility tree.\n"\
    #     "Please judge whether executing this action is helpful for finishing the target task,and give this action a rating, range from [1,3,7,9,10]. Give your score.\n"\
    #     "Also, you should give the reason or description for giving this score.\n"\
    #     f"Example output:{str(score_output)}\n"
    
    current_reward_prompt_system = '''You are an assistant to help navigate and operate the web page to achieve certain task.
        Your goal is to make an assessment of the action you are currently performing.
        "There are key information you will get:"
        **Key Information**:
            - previous trace: all thoughts and actions to complete this task step by step
            - current trace: current thoughts and actions performed 
            - accessibility tree: characteristic expression of the current web page
        
        "You will judge and score the currently performed action. The score ranges from 1-10, but the score you give can only be selected from [1, 3, 7, 9, 10]"
        **Judging and Scoring Criteria**:
            - score = 1: You may not have obtained accessibility tree information
            - score = 3: The action you performed (such as clicking on an element) does not help at all to complete the task
            - score = 7: The action you performed (such as clicking on an element) is helpful in completing this task
            - score = 9: This action you performed is a very critical intermediate step to complete this task
            - score = 10: This action is the last step to complete the task
        
        "You also need to provide an effective description of making the assessment"
        "A proper description contains:
            - Why do you give this score? 
            - What is the reason?
            - What would be better advice if given a low score? 
            - REMEMBER DO NOT LEAVE THE DESCRIPTION EMPTY!

        **Output Requirements**:
        - Ensure your output strictly follows this format:
            ```json
            {
                "score": "ACTUAL_SCORE",
                "description": ACTUAL_DESCRIPTION
            }
            ```
        - A VALID JSON BLOB EXAMPLE AS FELLOWS:
            ```
            {
                "score": "10",
                "description":"According to the previous trajectory, the current thought and the action performed are an important part of completing the target task, so it is very important. I give 9 points."
            }
            ```
    '''

    current_reward_prompt_user = "The target task here is described as \"{{user_request}}\".\n\n"\
        "The previous thought and action are:{{stringfy_previous_trace_output}}."\
        "The current thought and action is: {{stringfy_current_trace_output}}.\n\nYou have done the current action\n\n"\

    judge_searchbar_prompt_system = "You are an assistant to help navigate and operate the web page to achieve certain goals. Answer the following questions as best you can.\n"\
        "Your target is to judge whether the input is the search bar.\n"
    judge_searchbar_prompt_user = "Now the webpage's accessibility tree(the key information of current web page)is below: {{input_element}}\n"\
        "Last step you have fill in the input(id={{element_id}}) with text:{{action_input}}"\
        "Judge whether the input is the search bar. If the blank is search bar, return yes, else return no. You should only return one word!"

    semantic_match_prompt_system = "Now you are an assistant to judge whether 2 elements are semantically same. I'll provide a judge rule and an answer.\n"\
        "If they are the same, you should return 1. If they are not related, you should return 0. "\
        "If they are related but not identical, return a decimal (two decimal places) between 0 and 1 of the degree of relevance you think.\n"\
        "For example, the judge rule is: Decide whether the place is New York. The score of \"new york\" and \"纽约\" are both 1, \"Brooklyn\" should be 0.\n"\
        "However, if the judge rule is: Decide whether the place is in New York. The score of \"new york\" and \"纽约\" and \"Brooklyn\" are all 1.\n"\
        "Another example, the judge rule is: Decide whether I'm looking for clothes. The score of \"red Clothes\" and \"green jacket\"should also be 1.\n"\
        "However, if the judge rule is: Decide whether I'm looking for red clothes. the score of \"bright red Clothing\" could be 0.85(red include bright red but they are not the same), the score of \"green Clothes\"should be 0.5(red is not green).\n"\
        "Remember, you should return a number with ``` and an explanation. Like output: ```1```, (your explanation)"  # "Remember, you should only return a number without any punctuation or explanation!"

    semantic_match_prompt_user = "You should judge by the rule below:{{semantic_method}}.\n\nmy answer is:{{input_answer}}\n"
