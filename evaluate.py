import time
import json5
import requests
from agent.Environment.html_env.async_env import AsyncHTMLEnvironment
from evaluate import *
from agent.Plan import *
from playwright.async_api import Playwright, async_playwright, expect, Page
from agent.Environment.html_env.actions import create_action, Action, ActionTypes

import re
import asyncio
import argparse




# 解析命令行参数
parser = argparse.ArgumentParser(description="Run the agent in different modes.")
parser.add_argument("--mode", choices=["dom", "vision", "d_v"], default="d_v",
                    help="Choose interaction mode: 'dom' for DOM-based interaction, 'vision' for vision-based interaction, 'd_v' for DOM-based and vision-based interaction.")
args = parser.parse_args()
interaction_mode = args.mode


def read_file(path="./data/test.json"):
    '''读取标签数据'''
    with open(path) as f:
        test_data = json5.load(f)

    evaluation_data = test_data[0]["evaluation"]
    reference_task_length = test_data[0]["reference_task_length"]

    reference_evaluate_steps = []
    for i, evaluation in enumerate(evaluation_data):
        match_function = evaluation["match_function"]
        if "url" in match_function:
            key = evaluation["content"]["key"]
            reference_answer = evaluation["content"]["reference_answer"]
            reference_evaluate_steps.append({"match_function": match_function,
                                            "key": key, "reference_answer": reference_answer, "score": 0})
        elif "path" in match_function:  # TODO
            reference_answer = evaluation["content"]["reference_answer"]
            method = evaluation["method"]
            reference_evaluate_steps.append({"match_function": match_function, "method": method,
                                            "reference_answer": reference_answer, "score": 0})

    return reference_task_length, reference_evaluate_steps


async def step_evaluate(page: Page, evaluate_steps=[], input_path=None, semantic_method=None):
    '''评测步骤打分'''
    # reference_evaluate_steps, num_steps
    # num_steps += 1
    # page_url = html_env.page.url
    # page_url = page.url
    step_score = 0
    for evaluate in evaluate_steps:
        if evaluate["score"] != 1:
            match_function = evaluate["match_function"]
            if match_function == "url_exact_match":
                score = URLEvaluator.url_exact_match(
                    page.url, evaluate["reference_answer"], evaluate["key"])
            if match_function == "url_include_match":
                score = URLEvaluator.url_include_match(
                    page.url, evaluate["reference_answer"], evaluate["key"])
            if match_function == "url_semantic_match":
                score = URLEvaluator.url_semantic_match(
                    page.url, evaluate["reference_answer"], evaluate["key"], semantic_method=semantic_method)
            if match_function == "path_exact_match":
                method = evaluate["method"]
                print("path_exact_match:", input_path,
                      "***", evaluate["reference_answer"])
                score = PathEvaluator.path_exact_match(
                    input_path, evaluate["reference_answer"], method, await page.content())
            if match_function == "path_include_match":
                method = evaluate["method"]
                score = PathEvaluator.path_included_match(
                    input_path, evaluate["reference_answer"], method, await page.content())
            if match_function == "path_semantic_match":
                method = evaluate["method"]
                score = PathEvaluator.path_semantic_match(
                    input_path, evaluate["reference_answer"], method, await page.content(), semantic_method)
            if match_function == "text_exact_match":
                pass  # TODO
            if match_function == "text_include_match":
                pass
            if match_function == "text_semantic_match":
                pass

            evaluate["score"] = max(evaluate["score"], score)
        step_score += evaluate["score"]
    print("current step score:", step_score)
    return evaluate_steps
    # print(evaluate_steps)


async def aexec_playwright(code, page):
    '''async执行playwright代码'''
    exec(
        f'async def __ex(page): ' +
        ''.join(f'\n {l}' for l in code.split('\n'))
    )
    # Get `__ex` from local variables, call it and return the result
    return await locals()['__ex'](page)


async def main(num_steps=0, mode="dom"):

    reference_task_length, reference_evaluate_steps = read_file()
    print("raw data:\n", reference_evaluate_steps)

    # ! # 2. planning
    env = AsyncHTMLEnvironment(
        mode=mode,
        max_page_length=8192,
        headless=False,
        slow_mo=1000,
        current_viewport_only=False,
        viewport_size={"width": 1920, "height": 1280} if mode == "dom" else {"width": 1080, "height": 720},
        # "width": 1080, "height": 720
        save_trace_enabled=False,
        sleep_after_execution=0.0,
        locale="en-US",
        use_vimium_effect=True
    )
    observation_VforD = None
    if mode == "d_v":
        observation, observation_VforD = await env.reset("about:blank")
    else:
        observation = await env.reset("about:blank")

    previous_trace = []
    evaluate_steps = reference_evaluate_steps
    total_step_score = 0
    user_question = "Ask Satya Nadella to send an email and mention your interest in AI at linkdin"
    last_action_description = ""
    for index in range(10):
        print("planning前previous_trace：", previous_trace)
        print("planning前observation：", observation)
        for _ in range(3):
            try:
                dict_to_write = await Planning.plan(uuid=1, user_request=user_question, previous_trace=previous_trace, observation=observation,feedback = last_action_description,mode=mode, observation_VforD=observation_VforD)


                if dict_to_write is not None:
                    break
            except Exception as e:
                traceback.print_exc()
                continue

        def parse_current_trace(response):
            thought = response["description"].get("thought")
            action_type = response['action_type']
            acton_input = response['value']
            action = response["description"].get("action")
            current_trace = {"thought": thought, "action": action}
            try:
                element_id = int(response['id'])
            except:
                element_id = 0
            #! env.tree.nodeDict[element_id]勿动，调用映射关系，否则selector会出错
            if action_type in ["fill_form", "click"]:
                selector = env.tree.get_selector_and_xpath(
                    env.tree.nodeDict[element_id])
            else:
                selector = None
                element_id = 0
            execute_action = create_action(
                elementid=element_id, action_type=action_type, action_input=acton_input)
            return execute_action, current_trace, selector
        print("dict_to_write:", dict_to_write)

        if mode == "dom" or mode == "d_v":
            execute_action, current_trace, path = parse_current_trace(dict_to_write)
            selector, xpath = (path[0], path[1]) if path is not None else (None, None)
            print("current trace:\n", current_trace)
            print("response:\n", execute_action)
            print("selector:", selector)
            evaluate_steps = await step_evaluate(page=env.page, evaluate_steps=evaluate_steps, input_path=selector)
            print("执行动作前的url", env.page.url)
            for evaluate in evaluate_steps:
                total_step_score += evaluate["score"]
            if total_step_score == len(reference_evaluate_steps):
                break
            # input()
            if mode == "d_v":
                observation, observation_VforD = await env.execute_action(execute_action)
            else:
                observation = await env.execute_action(execute_action)
            print("执行动作后的url", env.page.url)

        elif mode == "vision":
            execute_action = dict_to_write["action"]
            thought = dict_to_write["description"].get("thought")
            action = dict_to_write["description"].get("action")
            current_trace = {"thought": thought, "action": action}
            print("执行动作前的url", env.page.url)
            if await env.vision_execute_action(execute_action):
                break
            print("vision_execute_action finished!")
            observation = await env._get_obs()
            print("执行动作后的url", env.page.url)

        if mode == "dom" or mode == "d_v":
            # current_trace = [current_trace]
            current_reward = await Planning.evaluate(user_request=user_question, previous_trace=previous_trace,
                                                     current_trace=current_trace, observation=observation)
            if current_reward and int(current_reward.get("score")) < 8:
                execute_action.update(
                    {"element_id": 0, "action_type": ActionTypes.GO_BACK})
                observation = await env.execute_action(execute_action)
                last_action_description = current_reward.get("description")
            else:
                last_action_description = ""
                previous_trace.append(current_trace)
        elif mode == "vision":
            previous_trace.append(current_trace)
            if dict_to_write["description"].get('reward'):
                if "loop" in dict_to_write["description"].get('reward').get("status"):
                    previous_trace = []
                    previous_trace.append(current_trace)

        input()
    # a = await Planning.plan(uuid=1, user_request="Find Dota 2 game and add all DLC to cart in steam.")
    # print(json5.dumps(a, indent=4))
    # input()


    # ! 3.任务评测打分
    if mode == "dom" or mode == "d_v":
        # step score
        total_step_score = 0
        for evaluate in evaluate_steps:
            total_step_score += evaluate["score"]
        print("\ntotal step score:", total_step_score)

        # length score
        task_evaluator = TaskLengthEvaluator()
        task_length_score = task_evaluator.task_length_score(reference_task_length, num_steps)
        print("task_length_score:", task_length_score)

        # finish score
        finish_task_score = FinishTaskEvaluator.finish_task_score(len(reference_evaluate_steps), total_step_score)
        print("finish_task_score:", finish_task_score)

        print(f"\033[31mtask finished!\033[0m")  # 红色
        input(f"\033[31m按回车键结束\033[0m")


if __name__ == "__main__":
    asyncio.run(main(mode=interaction_mode))
