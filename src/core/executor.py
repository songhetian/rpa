import time
import os
import re
import copy
import pyautogui
import pandas as pd
from datetime import datetime
from PySide6.QtCore import QThread, Signal
from core.models import AutomationScript, ActionStep
from core.web_engine import WebEngine
from utils.image_utils import ImageMatcher

class ScriptExecutor(QThread):
    log_signal = Signal(str, str)
    step_started = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, script: AutomationScript, parent_variables=None):
        super().__init__()
        self.script = script
        self.web_engine = WebEngine()
        # 初始化变量，支持从父流程传入
        self.variables = parent_variables if parent_variables is not None else copy.deepcopy(script.variables)
        self.is_running = True
        self.report_steps = []

    def stop(self): self.is_running = False

    def run(self):
        start_time = datetime.now()
        self.log_signal.emit(f"🚀 任务启动: {self.script.name}", "info")
        try:
            self.execute_steps(self.script.steps)
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"❌ 运行异常: {str(e)}", "error")
            self.finished_signal.emit(False)
        finally:
            self.web_engine.stop()

    def execute_steps(self, steps):
        for step in steps:
            if not self.is_running: break
            self.step_started.emit(step.id)
            if not self.execute_step(step):
                if not step.parameters.get("ignore_error", False):
                    raise Exception(f"步骤 {step.action_type} 执行失败")

    def resolve(self, text):
        if not isinstance(text, str): return text
        # 递归解析 {{var}} 语法
        matches = re.findall(r"\{\{(.*?)\}\}", text)
        for expr in matches:
            try:
                # 支持从 self.variables 中取值，或执行简单 Python 表达式
                val = eval(expr, {"__builtins__": None}, self.variables)
                text = text.replace(f"{{{{{expr}}}}}", str(val))
            except: pass
        return text

    def execute_step(self, step: ActionStep):
        if not step.enabled: return True
        p = {k: self.resolve(v) for k, v in step.parameters.items()}
        action = step.action_type
        
        try:
            # --- 1. 子流程与逻辑 ---
            if action == "call_subprocess":
                sub_path = p.get("sub_path", "")
                if os.path.exists(sub_path):
                    sub_script = AutomationScript.load(sub_path)
                    # 影刀模式：构建输入变量映射
                    sub_vars = {}
                    for k, v in step.arg_mappings.items():
                        # k 是子流程定义的参数名, v 是当前流程的变量名或值
                        sub_vars[k] = self.variables.get(v, v)
                    
                    sub_exec = ScriptExecutor(sub_script, parent_variables=sub_vars)
                    sub_exec.execute_steps(sub_script.steps)
                    
                    # 回传输出参数
                    for k, v in step.arg_mappings.items():
                        if k in sub_exec.variables: self.variables[v] = sub_exec.variables[k]
                    return True
                return False

            # --- 2. 动态指令执行 (针对语音意图生成的步骤) ---
            elif action == "ai_smart_step":
                # 这是一个“复合步骤”，它的子步骤是根据 prompt 动态生成的
                prompt = p.get("prompt", "")
                self.log_signal.emit(f"🤖 AI 正在解析意图: {prompt}", "info")
                # 模拟 AI 解析过程，将自然语言转为 ActionStep 列表
                # 在实际应用中，这里应调用 LLM API (如 Gemini/GPT)
                dynamic_steps = self.mock_ai_parser(prompt)
                self.execute_steps(dynamic_steps)
                return True

            # --- 3. 数据结构操作 (列表操作) ---
            elif action == "list_init":
                var_name = p.get("var", "my_list")
                self.variables[var_name] = []
                return True

            elif action == "list_append":
                list_var = p.get("list_var", "my_list")
                item_val = p.get("item_val", "")
                if list_var in self.variables and isinstance(self.variables[list_var], list):
                    self.variables[list_var].append(item_val)
                    self.log_signal.emit(f"📝 已添加数据到列表 {list_var}: {item_val}", "success")
                    return True
                return False

            # --- 4. 网页深度操作 ---
            elif action == "set_datetime":
                target = p.get("target", "")
                dt_val = p.get("value", "")
                js = f"document.querySelector('{target}').value = '{dt_val}'; document.querySelector('{target}').dispatchEvent(new Event('change'));"
                self.web_engine.page.evaluate(js)
                return True

            elif action == "get_text":
                target = p.get("target", "")
                var = p.get("var", "temp")
                val = self.web_engine.get_text(target)
                self.variables[var] = val
                return True

            # (其余基础动作...)
            if action == "open_url": self.web_engine.open_url(p.get("url"))
            elif action == "click": return self.web_engine.click_element(p.get("target"))
            elif action == "input": return self.web_engine.input_text(p.get("target"), p.get("text"))
            
            return True
        except Exception as e:
            self.log_signal.emit(f"步骤报错: {str(e)}", "error")
            return False

    def mock_ai_parser(self, prompt):
        """
        模拟 AI 指令解析逻辑
        用户说：'时间设置为2025-01-18 后获取价格 写入列表'
        """
        steps = []
        # 1. 解析日期设置
        if "时间" in prompt and "2025" in prompt:
            steps.append(ActionStep(action_type="set_datetime", 
                                    parameters={"target": "#date_picker", "value": "2025-01-18"}))
        # 2. 解析数据获取
        if "获取" in prompt:
            steps.append(ActionStep(action_type="get_text", 
                                    parameters={"target": ".price-tag", "var": "current_price"}))
        # 3. 解析列表写入
        if "列表" in prompt:
            steps.append(ActionStep(action_type="list_append", 
                                    parameters={"list_var": "result_list", "item_val": "{{current_price}}"}))
        return steps
