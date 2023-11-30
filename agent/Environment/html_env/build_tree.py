from lxml.html import etree
from io import StringIO
from collections import deque
from beartype import beartype
from beartype.door import is_bearable
from playwright.sync_api import (
    CDPSession,
    Page,
    Playwright,
    ViewportSize,
    expect,
    sync_playwright,
)
from .active_elements import ActiveElements
from .actions import (
    Action,
    ActionTypes,
    create_action
)
from .utils import (
    ElementNode,
    TagNameList,
    DelTagNameList,
)
import requests
import copy


class HTMLTree:
    def __init__(self):
        self.elementNodes = [ElementNode] * 100000
        self.rawNode2id: dict = {}
        self.element2id: dict = {}
        self.id2rawNode: dict = {}
        self.valid: list[bool] = [False] * 100000
        self.nodeCounts: int

    def fetch_html_content(self, html_content) -> None:
        self.__init__()
        parser = etree.HTMLParser()
        self.tree = etree.parse(StringIO(html_content), parser)
        self.copy_tree = copy.deepcopy(self.tree)
        root = self.tree.getroot()
        self.init_html_tree(root)
        self.build_html_tree(root)
        self.prune_tree()

    @staticmethod
    def build_node(node, idx: int) -> ElementNode:
        elementNode = ElementNode()
        elementNode["nodeId"] = idx
        elementNode["tagName"] = node.tag
        elementNode["text"] = node.text
        elementNode["attributes"] = node.attrib
        elementNode["childIds"] = []
        elementNode["parentId"] = ""
        elementNode["siblingId"] = ""
        elementNode["twinId"] = ""
        elementNode["depth"] = 1
        elementNode["htmlContents"] = etree.tostring(
            node, pretty_print=True).decode()
        return elementNode

    def build_mapping(self) -> None:
        self.element2id = {value["nodeId"]: index for index,
                           value in enumerate(self.elementNodes)}
        self.id2rawNode = {str(index): value for value,
                           index in self.rawNode2id.items()}

    def init_html_tree(self, root) -> None:
        node_queue = deque([root])
        node_id = 0
        while node_queue:
            node = node_queue.popleft()
            self.elementNodes[node_id] = HTMLTree().build_node(node, node_id)
            self.rawNode2id[node] = node_id
            node_id += 1
            for child in node.getchildren():
                node_queue.append(child)
        self.build_mapping()
        self.nodeCounts = node_id
        self.valid = self.valid[:self.nodeCounts + 1]

    def build_html_tree(self, root) -> None:
        node_queue = deque([root])
        root_id = self.rawNode2id[root]
        self.elementNodes[root_id]["parentId"] = -1
        while node_queue:
            node = node_queue.popleft()
            parent_id = self.rawNode2id[node]
            tag_st = {}
            sibling_id = 1
            for child in node.getchildren():
                child_id = self.rawNode2id[child]
                tag_name = self.elementNodes[child_id].get("tagName")
                tag_st[tag_name] = tag_st.get(tag_name, 0) + 1
                twin_id = tag_st.get(tag_name)
                self.elementNodes[parent_id]["childIds"].append(child_id)
                self.elementNodes[child_id]["parentId"] = parent_id
                self.elementNodes[child_id]["twinId"] = twin_id
                self.elementNodes[child_id]["depth"] = self.elementNodes[parent_id]["depth"] + 1
                self.elementNodes[child_id]["siblingId"] = sibling_id
                node_queue.append(child)
                sibling_id += 1
        self.pruningTreeNode = copy.deepcopy(self.elementNodes)

    def get_node_info(self, idx: int, pruning: bool = True) -> None:
        if pruning is True:
            elementNode = self.pruningTreeNode[idx]
        else:
            elementNode = self.elementNodes[idx]
        print("*" * 10)
        print("nodeId: ", elementNode["nodeId"])
        print("childIds: ", elementNode["childIds"])
        print("parentId:", elementNode["parentId"])
        print("siblingId:", elementNode["siblingId"])
        print("depth:", elementNode["depth"])
        print("tagName: ", elementNode["tagName"])
        print("text: ", elementNode["text"])
        print("attributes: ", elementNode["attributes"])
        print("htmlcontents:", elementNode["htmlContents"])
        print("*" * 10)
        print(" " * 10)

    def get_xpath(self, idx: int) -> str:
        locator_str = ""
        current_node = self.elementNodes[idx]
        tag_name = current_node["tagName"]
        twinId = current_node["twinId"]
        locator_str = "/" + tag_name + "[" + str(twinId) + "]"
        while current_node["parentId"] != 0:
            parentid = current_node["parentId"]
            current_node = self.elementNodes[parentid]
            current_tag_name = current_node["tagName"]
            twinId = current_node["twinId"]
            locator_str = "/" + current_tag_name + \
                "[" + str(twinId) + "]" + locator_str
        parentid = current_node["parentId"]
        current_node = self.elementNodes[parentid]
        current_tag_name = current_node["tagName"]
        return "/" + current_tag_name + locator_str

    def get_selector(self, idx: int) -> str:
        selector_str = ""
        current_node = self.elementNodes[idx]
        while current_node["parentId"] != -1:
            tag_name = current_node["tagName"]
            siblingId = str(current_node["siblingId"])
            if current_node["attributes"].get('id'):
                return "#" + current_node["attributes"].get('id') + selector_str
            if len(self.elementNodes[current_node["parentId"]]["childIds"]) > 1:
                uu_node = True
                for childId in self.elementNodes[current_node["parentId"]]["childIds"]:
                    bro_node = self.elementNodes[childId]
                    if bro_node["nodeId"] != current_node["nodeId"] and current_node["attributes"].get('class') and bro_node["attributes"].get("class") == current_node["attributes"].get('class'):
                        uu_node = False
                        break
                if current_node["attributes"].get('class') and uu_node is True:
                    selector_str = " > " + tag_name + "." + \
                        ".".join(current_node["attributes"].get(
                            'class').replace("\n", " ").split(" ")) + selector_str
                else:
                    selector_str = " > " + tag_name + \
                        ":nth-child(" + siblingId + ")" + selector_str
            else:
                selector_str = " > " + tag_name + selector_str
            current_node = self.elementNodes[current_node["parentId"]]
        return current_node["tagName"] + selector_str

    def xpath_element(self, locator_str: str) -> None:
        try:
            elements = self.copy_tree.xpath(locator_str)
            element = elements[0]
            if element is not None:
                print(element.tag, element.attrib, element.text)
        except Exception as e:
            print(
                f"error occur {e}")

    def select_element(self, locator_str: str) -> None:
        try:
            elements = self.copy_tree.getroot().cssselect(locator_str)
            element = elements[0]
            if element is not None:
                print(element.tag, element.attrib, element.text)
        except Exception as e:
            print(
                f"error occur {e}")

    def is_valid(self, idx: int) -> bool:
        node = self.pruningTreeNode[idx]
        if node["tagName"] in TagNameList:
            return ActiveElements.is_valid_element(node)

    # 通过后序遍历判断是否是有效tag
    def prune_tree(self) -> str:
        """遍历每个元素判断是否有效并剪枝"""
        result_list = []
        root = self.pruningTreeNode[0]
        if root is None:
            result_list = []
        stack = [root]
        while stack:
            node = stack.pop()
            nodeId = node["nodeId"]
            result_list.append(nodeId)
            children = []
            for childId in node["childIds"]:
                childNode = self.pruningTreeNode[childId]
                children.append(childNode)
            stack.extend(children)
        result = result_list[::-1]
        for nodeId in result:
            if self.is_valid(nodeId) or self.valid[nodeId] is True:
                rawNode = self.id2rawNode[str(nodeId)]
                html_contents = etree.tostring(
                    rawNode, pretty_print=True).decode()
                self.pruningTreeNode[nodeId]["htmlContents"] = html_contents
                self.valid[nodeId] = True
                current_id = nodeId
                while self.pruningTreeNode[current_id]["parentId"] != -1:
                    parent_id = self.pruningTreeNode[current_id]["parentId"]
                    self.valid[parent_id] = True
                    current_id = parent_id
            else:
                rawNode = self.id2rawNode[str(nodeId)]
                rawNode.getparent().remove(rawNode)
                current_node = self.pruningTreeNode[nodeId]
                current_node["htmlContents"] = ""
                parentid = current_node["parentId"]
                self.pruningTreeNode[parentid]["childIds"].remove(nodeId)
                self.valid[nodeId] = False
        return self.pruningTreeNode[0]["htmlContents"]

    def get_element_contents(self, idx: int) -> str:
        node = self.elementNodes[idx]
        html_content = node["htmlContents"]
        return html_content

    def get_tag_name(self, element: ElementNode) -> (str, int):
        tag_name = ActiveElements.get_element_tagName(element)
        tag_idx = element["nodeId"]
        if tag_name == "unknown":
            tag_name = element["tagName"]
            tag_idx = element["nodeId"]
            # TODO 添加更多映射关系
            if tag_name == "span":
                parent_element = self.elementNodes[element["parentId"]]
                return self.get_tag_name(parent_element)
            else:
                return ("statictext", tag_idx)
        return (tag_name, tag_idx)

    def build_dom_tree(self) -> str:
        root = self.pruningTreeNode[0]
        stack = [root]
        contents = ""
        while stack:
            node = stack.pop()
            # if len(node["childIds"]) == 0 and self.valid[node["nodeId"]] is True:
            if self.valid[node["nodeId"]] is True:
                content_text = HTMLTree().process_element_contents(node)
                if content_text != "":
                    tag_name, _ = self.get_tag_name(
                        node)
                    # 选择node["nodeId"]还是父节点可交互元素的idx
                    contents += " " * (node["depth"]-1) + "[" + str(node["nodeId"]) + "] " + tag_name + \
                        " " + f"\'{content_text}\'" + "\n"
            children = []
            for child_id in node["childIds"]:
                children.append(self.pruningTreeNode[child_id])
            stack.extend(reversed(children))
        return contents

    def get_parents_id(self, idx: int) -> (str, str, str):
        parentid_str = ""
        parent_tag_str = ""
        current_node = self.elementNodes[idx]
        nodeId = current_node["nodeId"]
        tagName = current_node["tagName"]
        twinId = current_node["twinId"]
        parent_tag_str += tagName + "->"
        parentid_str += str(nodeId) + "->"
        twinId_str = str(twinId) + "->"
        while current_node["parentId"] != -1:
            nodeId = current_node["parentId"]
            current_node = self.elementNodes[nodeId]
            tagName = current_node["tagName"]
            twinId = current_node["twinId"]
            parent_tag_str += tagName + "->"
            parentid_str += str(nodeId) + "->"
            twinId_str += str(twinId) + "->"
        parentid_str += "-1"
        return parentid_str, parent_tag_str, twinId_str

    def get_selector_and_xpath(self, idx: int) -> (str, str):
        try:
            return self.get_selector(idx), self.get_xpath(idx)
        except Exception as e:
            print(
                f"can't locate element,error occur {e}")

    @staticmethod
    def process_element_contents(element: ElementNode) -> str:
        # TODO 添加合适的可交互元素信息，目前只处理具有text属性的可交互元素
        html_text = ActiveElements.get_element_value(element)
        if html_text is None:
            return ""
        return html_text.replace("\n", "").replace("\t", "").strip()

    def get_elements_distance(self, idx1: int, idx2: int) -> int:
        element1, element2 = self.elementNodes[idx1], self.elementNodes[idx2]
        if element1["depth"] < element2["depth"]:
            return self.get_distance(idx2, idx1)
        higher_element, lower_element = element1, element2
        while higher_element["depth"] - lower_element["depth"] > 0:
            higher_element = self.elementNodes[higher_element["parentId"]]
        while higher_element["nodeId"] != lower_element["nodeId"]:
            higher_element = self.elementNodes[higher_element["parentId"]]
            lower_element = self.elementNodes[lower_element["parentId"]]
        return element1["depth"] + element2["depth"] - 2 * lower_element["depth"]


class HTMLEnvironment:
    @beartype
    def __init__(
        self,
        max_page_length: int = 8192,
        headless: bool = True,
        slow_mo: int = 0,
        current_viewport_only: bool = False,
        viewport_size: ViewportSize = {"width": 1280, "height": 720},
        save_trace_enabled: bool = False,
        sleep_after_execution: float = 0.0,
    ):
        self.headless = headless
        self.slow_mo = slow_mo
        self.current_viewport_only = current_viewport_only
        self.reset_finished = False
        self.viewport_size = viewport_size
        self.save_trace_enabled = save_trace_enabled
        self.sleep_after_execution = sleep_after_execution
        self.tree = HTMLTree()

    def setup(self, start_url: str) -> None:
        self.context_manager = sync_playwright()
        self.playwright = self.context_manager.__enter__()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        start_url = start_url
        self.context = self.browser.new_context(
            viewport=self.viewport_size,
            device_scale_factor=1,
        )
        if start_url:
            start_urls = start_url.split(" |AND| ")
            for url in start_urls:
                self.page = self.context.new_page()
                client = self.page.context.new_cdp_session(
                    self.page
                )
                self.page.client = client
                self.page.goto(url)
                self.page.wait_for_timeout(500)
                self.html_content = self.page.content()
        else:
            self.page = self.context.new_page()

    def _get_obs(self):
        self.tree.fetch_html_content(self.html_content)
        return self.tree.build_dom_tree()

    def reset(self, start_url: str) -> str:
        if start_url:
            self.setup(start_url)
        observation = self._get_obs()
        return observation

    def execute_action(self, action: Action) -> str:
        '''找到可交互元素并执行相应的动作得到新的observation'''
        element_name, element_idx = self.tree.get_tag_name(
            self.tree.elementNodes[action["element_id"]])
        action.update({"element_id": element_idx,
                      "element_name": element_name})
        selector, xpath = self.tree.get_selector_and_xpath(
            action["element_id"])
        try:
            match action["action_type"]:
                case ActionTypes.CLICK:
                    try:
                        self.page.locator(selector).click()
                        self.html_content = self.page.content()
                        return self._get_obs()
                    except Exception as e:
                        print("can't execute click action")
                        print(e)
                        return ""
                case ActionTypes.GOTO:
                    try:
                        self.page = self.context.new_page()
                        self.page.goto(action["url"])
                        self.html_content = self.page.content()
                        return self._get_obs()
                    except Exception as e:
                        print("can't execute goto action")
                        print(e)
                        return ""
                case ActionTypes.FILL_FORM:
                    try:
                        self.page.locator(selector).fill(action["fill_text"])
                        self.page.locator(selector).press("Enter")
                        self.html_content = self.page.content()
                        return self._get_obs()
                    except Exception as e:
                        print("can't execute fill form action")
                        print(e)
                        return ""
                case ActionTypes.GOOGLE_SEARCH:
                    try:
                        self.page = self.context.new_page()
                        self.page.goto(action["url"])
                        search_box = self.page.query_selector(
                            'textarea[name="q"]')
                        if search_box is not None:
                            search_box.fill(action["fill_text"])
                            self.page.click('input[type="submit"]')
                        self.html_content = self.page.content()
                        return self._get_obs()
                    except Exception as e:
                        print("can't execute google search action")
                        print(e)
                        return ""
                case _:
                    raise ValueError(
                        f"Unknown action type {action['action_type']}"
                    )
        except Exception as e:
            print("execute goto action")
            print(e)
        return ""
