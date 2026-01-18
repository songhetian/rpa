from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import uuid

@dataclass
class Parameter:
    """参数定义：用于子流程输入输出"""
    name: str
    description: str = ""
    default_value: Any = None
    type: str = "string" # string, int, list, dict

@dataclass
class ActionStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    # 影刀式参数映射：{ "子流程输入名": "主流程变量名" }
    arg_mappings: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    children: List['ActionStep'] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id, "action_type": self.action_type,
            "parameters": self.parameters, "arg_mappings": self.arg_mappings,
            "enabled": self.enabled, "children": [c.to_dict() for c in self.children]
        }

@dataclass
class Trigger:
    """触发器定义"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: str = "time"  # time (定时), hotkey (快捷键)
    script_path: str = "" # 触发哪个脚本
    config: Dict[str, Any] = field(default_factory=dict) # 存储 cron 表达式或键位
    enabled: bool = True

    def to_dict(self):
        return vars(self)

@dataclass
class AutomationScript:
# ... (其余部分保持不变)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新脚本"
    # 脚本的“接口”定义
    inputs: List[Parameter] = field(default_factory=list)
    outputs: List[Parameter] = field(default_factory=list)
    steps: List[ActionStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "inputs": [vars(p) for p in self.inputs],
            "outputs": [vars(p) for p in self.outputs],
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables
        }

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
            script = cls(id=d.get('id', str(uuid.uuid4())), name=d.get('name', 'Script'))
            script.inputs = [Parameter(**p) for p in d.get('inputs', [])]
            script.outputs = [Parameter(**p) for p in d.get('outputs', [])]
            script.variables = d.get('variables', {})
            
            def load_steps(step_dicts):
                steps = []
                for sd in step_dicts:
                    s = ActionStep(id=sd.get('id', str(uuid.uuid4())), 
                                   action_type=sd['action_type'],
                                   parameters=sd.get('parameters', {}),
                                   arg_mappings=sd.get('arg_mappings', {}),
                                   enabled=sd.get('enabled', True))
                    s.children = load_steps(sd.get('children', []))
                    steps.append(s)
                return steps
            script.steps = load_steps(d.get('steps', []))
            return script
