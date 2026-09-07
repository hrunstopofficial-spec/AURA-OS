import os
import sys
import json
import logging
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import GROQ_API_KEY, DRIVE_VAULT_URL, DRIVE_FOLDER_ID
from memory.memory_manager import MemoryManager
from tools import pc_tools
from groq import Groq
from brain.intent_router import IntentRouter
from brain.cognitive_router import CognitiveRouter, CognitiveRoute
from brain.device_presence_router import DevicePresenceRouter
from brain.codeact_cloud_runner import CodeActCloudRunner
from app.agents.swarm import SwarmOrchestrator
import asyncio

logger = logging.getLogger(__name__)


def _run_async_safely(coro):
    """
    Safely executes an async coroutine whether or not an asyncio event loop is already running.
    Prevents 'RuntimeError: asyncio.run() cannot be called from a running event loop'.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "create_placement_sprint",
            "description": "Create a temporary high-intensity placement drive sprint (e.g. Capgemini, TCS, Zoho drive prep) that overrides the daily schedule for a specific number of days and auto-reverts back to baseline routine on deadline completion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Name of the company or placement drive event (e.g. 'Capgemini Placement Sprint', 'TCS NQT Prep')."
                    },
                    "duration_days": {
                        "type": "integer",
                        "description": "Duration of the sprint in days (default 7)."
                    }
                },
                "required": ["company_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_schedule",
            "description": "Get today's active schedule (shows active sprint override if in progress, or baseline Java/Python/Aptitude routine).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_browser_url",
            "description": "Open any website, URL, or web service (e.g. Gmail, YouTube, Google, GitHub, LinkedIn, ChatGPT) directly on Mukil's PC screen in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The exact web URL to open (e.g. 'https://mail.google.com', 'https://youtube.com', 'https://github.com')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "Execute any PowerShell command on Mukil's Windows PC. Use for getting battery info, launching apps/browsers (e.g. Start-Process 'https://mail.google.com'), checking processes, git commands, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The exact PowerShell command line to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder/directory on Mukil's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute or relative folder path (e.g. C:/Users/mukil/Desktop/NewProject)."
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "Create or write content to a file on Mukil's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Target file path on PC."
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write into the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_text_file",
            "description": "Read file contents from Mukil's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path on PC to read."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and subfolders in a directory on Mukil's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Directory path on PC to inspect."
                    }
                },
                "required": ["directory_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_drive_vault_info",
            "description": "Get the URL and details of Mukil's 5TB Google Drive Master Vault.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Automate sending a WhatsApp message to a specific contact on Mukil's PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string",
                        "description": "The contact or person name to search for (e.g. 'Amma', 'Mukil', 'Dad')."
                    },
                    "message": {
                        "type": "string",
                        "description": "The exact message to send."
                    }
                },
                "required": ["contact_name", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_screen_brightness",
            "description": "Set PC screen brightness percentage (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Brightness percentage from 0 to 100."
                    }
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_screen_brightness",
            "description": "Get current PC screen brightness level.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_system_volume",
            "description": "Set PC master audio volume percentage (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level percentage from 0 to 100."
                    }
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_pc_screenshot",
            "description": "Take a screenshot of the PC screen and save it.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_workstation",
            "description": "Lock the Windows PC immediately.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_indeed_jobs",
            "description": "Launch autonomous browser to search and apply for jobs on Indeed India.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "Job title or keywords (e.g. 'Software Engineer', 'Python Developer', 'AI Engineer')."
                    },
                    "location": {
                        "type": "string",
                        "description": "Job location (e.g. 'Remote', 'Bangalore', 'Tamil Nadu')."
                    },
                    "max_applications": {
                        "type": "integer",
                        "description": "Number of job applications to process (e.g. 2 or 3)."
                    }
                },
                "required": ["keywords"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube_song",
            "description": "Search and play any song or video on YouTube in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song name or YouTube search query (e.g. 'Believer', 'Arabic Kuthu', 'Lofi beats')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "Use autonomous Chrome browser to search Google for information, links, and summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_and_screenshot",
            "description": "Open any website URL in Chrome, take a screenshot of the page, and return it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full website URL to visit."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read_page",
            "description": "Visit any website URL and extract its text content for analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The website URL to read."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_auto_fill_form",
            "description": "Visit a website URL/form and automatically fill fields with Mukil's profile details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The form or portal website URL."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_apply_job",
            "description": "Autonomously apply for a job on any career portal or company website (e.g. Zoho, Freshworks, Swiggy, Capgemini, Postman). Automatically fills Mukil's profile, attaches master PDF resume, captures live proof screenshot, and tracks the application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "The target company name (e.g. 'Zoho', 'Freshworks', 'Swiggy', 'Postman', 'Capgemini')."
                    },
                    "role": {
                        "type": "string",
                        "description": "The target role (e.g. 'AI Engineer', 'Software Engineer', 'Python Developer')."
                    },
                    "url": {
                        "type": "string",
                        "description": "Optional direct job portal URL."
                    }
                },
                "required": ["company"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_file_slice",
            "description": "View a specific line range slice of a code file with 1-based indexing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute or relative file path to view."},
                    "start_line": {"type": "integer", "description": "Starting line number (1-indexed)."},
                    "end_line": {"type": "integer", "description": "Ending line number (1-indexed)."}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_file_content",
            "description": "Perform an atomic surgical search-and-replace edit on a file without rewriting the entire file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Target file to edit."},
                    "target_content": {"type": "string", "description": "The exact existing text chunk to replace."},
                    "replacement_content": {"type": "string", "description": "The new replacement text chunk."}
                },
                "required": ["file_path", "target_content", "replacement_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Create a new file or overwrite an existing file cleanly on disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Target file path."},
                    "code_content": {"type": "string", "description": "Full file content to write."},
                    "overwrite": {"type": "boolean", "description": "Whether to overwrite if file exists."}
                },
                "required": ["file_path", "code_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Perform fast regex or keyword pattern search across code files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search pattern or keyword."},
                    "search_path": {"type": "string", "description": "Directory path to search in."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_by_name",
            "description": "Find files and directories matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g. '*.py', 'login*')."},
                    "search_path": {"type": "string", "description": "Directory to search in."}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command_and_heal",
            "description": "Execute a shell command with autonomous self-healing and error correction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "PowerShell command to execute."},
                    "cwd": {"type": "string", "description": "Working directory path."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_subagent",
            "description": "Delegate a deep research, coding, placement, or finance task to a specialized background subagent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subagent_name": {"type": "string", "description": "Subagent type: 'research', 'coder', 'placement_hunter', or 'finance_analyst'."},
                    "task_prompt": {"type": "string", "description": "Detailed actionable task prompt for the subagent."}
                },
                "required": ["subagent_name", "task_prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "tailor_ats_resume",
            "description": "Tailor Mukil's Master Resume for a specific company and job description, calculate ATS score (>90%), and generate customized cover letter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Target company name (e.g. 'Zoho', 'Freshworks', 'Swiggy')."},
                    "role": {"type": "string", "description": "Target role (e.g. 'AI Engineer', 'Software Developer')."},
                    "jd_text": {"type": "string", "description": "Optional Job Description text or requirements."}
                },
                "required": ["company", "role"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sgc_billing_data",
            "description": "Query Sri Ganapathi Colours (SGC) yarn dyeing billing database for latest bills, specific customer/party amounts (e.g. MSK Fabrics, Sowbhagiya, GAIA), or total pending ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Optional customer or party name to filter by (e.g. 'MSK Fabrics', 'Sowbhagiya', 'GAIA')."},
                    "query": {"type": "string", "description": "Natural language query about SGC business bills or overdue."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": "Store or recall persistent user facts/notes, allocate project workspaces, or view all active memory allocations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["store_fact", "allocate_project", "check_allocations"], "description": "Action to perform: 'store_fact' to save a custom user fact/note, 'allocate_project' to allocate memory for a software project, or 'check_allocations' to view all persistent memory partitions."},
                    "key": {"type": "string", "description": "Topic or key name for the fact (e.g. 'favourite_tech', 'friend_info')."},
                    "value": {"type": "string", "description": "Content or details of the fact to store."},
                    "project_name": {"type": "string", "description": "Project name when allocating project memory."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_cloud_server",
            "description": "Check Render cloud production server health, sync memory between PC and cloud, or check 24/7 keep-alive status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["status", "sync_memory"], "description": "Action: 'status' to check cloud server health & uptime, or 'sync_memory' to sync local memory to cloud DB."}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_push_changes",

            "description": "Autonomously stage all changes, commit with a professional message, and push directly to Mukil's AURA-OS GitHub repository without asking for credentials or repo URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_message": {
                        "type": "string",
                        "description": "Descriptive commit message (e.g. 'feat: physical execution engine and hardware vitals')."
                    }
                }
            }
        }
    }
]


# Dynamically append tools registered via @aura_tool (e.g. system vitals, hardware, diagnosis)
from tools.registry import registry
from tools import system_tools

for _schema in registry.get_schemas():
    if not any(t.get("function", {}).get("name") == _schema["function"]["name"] for t in TOOLS_DEFINITION):
        TOOLS_DEFINITION.append(_schema)

class AgentBrain:
    def __init__(self):
        self.mem = MemoryManager()
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "openai/gpt-oss-120b"
        self.fast_model = "openai/gpt-oss-20b"
        self.router = IntentRouter()
        self.cognitive_router = CognitiveRouter()
        self.device_router = DevicePresenceRouter()
        self.swarm = SwarmOrchestrator()
        self.codeact_runner = CodeActCloudRunner()

    def _chat_complete(self, messages, tools=None, tool_choice="auto", temperature=0.4, max_tokens=1000):
        """Executes chat completion with seamless fallback to fast_model on 429 or 404."""
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as err:
            err_str = str(err).lower()
            if "429" in err_str or "rate_limit" in err_str or "404" in err_str or "not found" in err_str:
                logger.warning(f"Falling back to {self.fast_model} due to: {err}")
                return self.client.chat.completions.create(
                    model=self.fast_model,
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            raise err

    def _execute_tool_sync(self, name: str, args: dict) -> str:
        # Check central tool registry first
        tool_def = registry.get_tool(name)
        if tool_def:
            res = tool_def.execute(**args)
            if res["success"]:
                if isinstance(res["result"], (dict, list)):
                    return json.dumps(res["result"], indent=2)
                return str(res["result"])
            return f"Tool {name} execution error: {res['error']}"

        if name == "auto_apply_job":
            return pc_tools.auto_apply_job(
                company=args.get("company", "Tech Company"),
                role=args.get("role", "AI Engineer"),
                url=args.get("url")
            )
        elif name == "create_placement_sprint":
            sched = AdaptiveScheduler()
            res = sched.create_sprint_override(
                event_name=args.get("company_name", "Placement Drive Sprint"),
                duration_days=args.get("duration_days", 7)
            )
            return f"✅ 7-Day Sprint '{res['sprint_name']}' created successfully! Expiry Date: {res['expiry_date']}. Daily schedule has been prioritized for this drive and will auto-revert upon completion."
        elif name == "get_daily_schedule":
            sched = AdaptiveScheduler()
            res = sched.get_today_active_schedule()
            return f"📅 Today's Active Schedule (Mode: {res['mode']}):\n" + json.dumps(res['schedule'], indent=2)
        elif name == "open_browser_url":
            return pc_tools.open_browser_url(args.get("url", "https://google.com"))
        elif name == "run_powershell":
            return pc_tools.run_powershell(args.get("command", ""))
        elif name == "create_folder":
            return pc_tools.create_folder(args.get("folder_path", ""))
        elif name == "write_text_file":
            return pc_tools.write_text_file(args.get("file_path", ""), args.get("content", ""))
        elif name == "read_text_file":
            return pc_tools.read_text_file(args.get("file_path", ""))
        elif name == "list_files":
            return pc_tools.list_files(args.get("directory_path", ""))
        elif name == "get_drive_vault_info":
            return f"5TB Drive Vault URL: {DRIVE_VAULT_URL} (Folder ID: {DRIVE_FOLDER_ID})"
        elif name == "send_whatsapp_message":
            return pc_tools.send_whatsapp_message(args.get("contact_name", ""), args.get("message", ""))
        elif name == "set_screen_brightness":
            return pc_tools.set_screen_brightness(args.get("level", 100))
        elif name == "get_screen_brightness":
            return pc_tools.get_screen_brightness()
        elif name == "set_system_volume":
            return pc_tools.set_system_volume(args.get("level", 50))
        elif name == "take_pc_screenshot":
            return pc_tools.take_pc_screenshot()
        elif name == "lock_workstation":
            return pc_tools.lock_workstation()
        elif name == "apply_indeed_jobs":
            return pc_tools.apply_indeed_jobs(
                keywords=args.get("keywords", "Software Engineer"),
                location=args.get("location", "Remote"),
                max_applications=args.get("max_applications", 3)
            )
        elif name == "play_youtube_song":
            return pc_tools.play_youtube_song(args.get("query", "Believer"))
        elif name == "browser_search":
            return pc_tools.browser_search(args.get("query", ""))
        elif name == "browser_open_and_screenshot":
            return pc_tools.browser_open_and_screenshot(args.get("url", ""))
        elif name == "browser_read_page":
            return pc_tools.browser_read_page(args.get("url", ""))
        elif name == "browser_auto_fill_form":
            return pc_tools.browser_auto_fill_form(args.get("url", ""))
        elif name == "view_file_slice":
            from brain.agentic_engine import view_file_slice
            return view_file_slice(args.get("file_path", ""), args.get("start_line", 1), args.get("end_line", 100))
        elif name == "replace_file_content":
            from brain.agentic_engine import replace_file_content
            return replace_file_content(args.get("file_path", ""), args.get("target_content", ""), args.get("replacement_content", ""))
        elif name == "write_to_file":
            from brain.agentic_engine import write_to_file
            return write_to_file(args.get("file_path", ""), args.get("code_content", ""), args.get("overwrite", True))
        elif name == "grep_search":
            from brain.agentic_engine import grep_search
            return grep_search(args.get("query", ""), args.get("search_path"))
        elif name == "find_by_name":
            from brain.agentic_engine import find_by_name
            return find_by_name(args.get("pattern", ""), args.get("search_path"))
        elif name == "run_command_and_heal":
            from brain.agentic_engine import run_command_and_heal
            res = run_command_and_heal(args.get("command", ""), args.get("cwd"))
            return json.dumps(res, indent=2)
        elif name == "invoke_subagent":
            from brain.agentic_engine import swarm
            res = swarm.invoke(args.get("subagent_name", "research"), args.get("task_prompt", ""))
            return json.dumps(res, indent=2)
        elif name == "tailor_ats_resume":
            from agents.placement_tailor_agent import ATSResumeTailorAgent
            tailor = ATSResumeTailorAgent()
            res = tailor.tailor_resume_for_job(args.get("company", "Tech Company"), args.get("role", "Software Engineer"), args.get("jd_text", ""))
            return json.dumps(res, indent=2)
        elif name == "get_sgc_billing_data":
            from app.agents.swarm.sgc_executive_agent import SGCExecutiveAgent
            from app.agents.swarm.base_swarm_agent import SwarmTaskMessage
            agent = SGCExecutiveAgent()
            msg = SwarmTaskMessage(
                task_id="tool_sgc",
                sender="AgentBrain",
                recipient="SGCExecutive",
                action="GET_LATEST_BILL",
                payload={"query": args.get("query", ""), "customer": args.get("customer_name", "")}
            )
            res = _run_async_safely(agent.process_task(msg))
            return res.result.get("summary", "No billing data found.") if res.result else "No billing data found."
        elif name == "manage_memory":
            from app.agents.swarm.memory_vault_agent import MemoryVaultAgent
            from app.agents.swarm.base_swarm_agent import SwarmTaskMessage
            agent = MemoryVaultAgent()
            act = args.get("action", "check_allocations").lower()
            if "store" in act or "save" in act:
                action = "STORE_FACT"
            elif "project" in act or "allocate" in act:
                action = "ALLOCATE_PROJECT_MEMORY"
            else:
                action = "CONFIRM_MEMORY_STATUS"
            msg = SwarmTaskMessage(
                task_id="tool_mem",
                sender="AgentBrain",
                recipient="MemoryVault",
                action=action,
                payload=args
            )
            res = _run_async_safely(agent.process_task(msg))
            return res.result.get("summary", "Memory updated.") if res.result else "Memory updated."
        elif name == "manage_cloud_server":
            from app.agents.swarm.server_agent import ServerAgent
            from app.agents.swarm.base_swarm_agent import SwarmTaskMessage
            agent = ServerAgent()
            act = args.get("action", "status").lower()
            action = "SYNC_MEMORY" if "sync" in act else "CHECK_SERVER_STATUS"
            msg = SwarmTaskMessage(
                task_id="tool_srv",
                sender="AgentBrain",
                recipient="ServerAgent",
                action=action,
                payload=args
            )
            res = _run_async_safely(agent.process_task(msg))
            return res.result.get("summary", "Server status checked.") if res.result else "Server status checked."
        elif name == "git_push_changes":
            msg = args.get("commit_message") or "feat(core): enhance physical interactive execution bridge and hardware vitals engine"
            subprocess.run(["git", "add", "."], capture_output=True, text=True)
            c_res = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
            p_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
            out = f"Git Push Output:\nCommit: {c_res.stdout or c_res.stderr}\nPush: {p_res.stdout or p_res.stderr}"
            return out
        else:
            return f"Unknown tool: {name}"


    def execute_tool(self, name: str, args: dict) -> str:
        logger.info(f"Executing tool: {name} with args: {args}")
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._execute_tool_sync, name, args)
                return future.result(timeout=120)
        except Exception as e:
            logger.error(f"Tool execution failed for {name}: {e}")
            return f"Tool {name} execution failed: {str(e)}"

    def process_message(self, user_message: str, user_name: str = "Mukil") -> str:
        sys_context = self.mem.get_system_prompt_context()
        system_prompt = (
            f"You are AURA (also known as JARVIS), {user_name}'s ultra-intelligent personal AI executive partner, autonomous engineer, and close co-developer brother.\n\n"
            "🌟 SCRIPT & SPEECH SYNTHESIS DIRECTIVE (CRITICAL - FLAWLESS PRONUNCIATION):\n"
            "- ALWAYS write in standard English alphabet (Roman letters only). NEVER mix Tamil unicode script characters (like 'என்ன task-ஐ', 'thinking-ல்', 'fire-அப்') into the text!\n"
            "- When replying in Tanglish, ALWAYS use pure Romanized letters (e.g. 'Enna task start pannalaam Boss? Auto-apply-aa illa screenshot dispatcher-aa? Sollunga, ready pannidalaam!').\n"
            "- If Mukil types in English, reply in clean, articulate, sharp English ('Got it Boss, on it!').\n"
            "- This guarantees that text-to-speech (TTS) neural voice pronounces every single word naturally, clearly, and smoothly without stumbling!\n"
            "- For greetings (e.g. 'epdi irukka?', 'what's up?'): Give a short, friendly 2-sentence reply without dumping feature lists.\n"
            "🤝 COLLABORATIVE BRAINSTORMING & ARCHITECTURAL PROTOCOL:\n"
            "- When Mukil discusses a new project idea, product concept, UI design, or business plan:\n"
            "  1. Validate the idea with genuine excitement and senior engineering insight.\n"
            "  2. Ask 2-3 concise, high-value clarifying questions to understand his exact vision (e.g. 'Theme preference enna?', 'OAuth or Email login?', 'What animations to include?').\n"
            "  3. Ask for confirmation before building: 'Semma idea maapla! Idhula [features] vachu live-aa build panni localhost preview link kudukkatava?'\n"
            "  4. NEVER dump raw multi-line code files, HTML, CSS, or JS into the chat window!\n"
            "- Once Mukil gives the green light ('aama build pannu' / 'ok done'), AUTONOMOUSLY build the files on disk, host them on localhost/tunnel, and give him the direct clickable live preview URL!\n\n"
            + sys_context
        )

        # Assemble Multi-Turn Messages with Recent Conversation History
        messages = [{"role": "system", "content": system_prompt}]
        recent_history = self.mem.get_recent_conversations(limit=6)
        for turn in recent_history:
            role = "user" if turn.get("sender") == user_name else "assistant"
            messages.append({"role": role, "content": turn.get("text", "")})
        messages.append({"role": "user", "content": user_message})

        try:
            # ── DYNAMIC THINKING & ACTION (ReAct) LOOP ─────────────────────────
            for turn in range(5):
                response = self._chat_complete(
                    messages=messages,
                    tools=TOOLS_DEFINITION,
                    tool_choice="auto",
                    temperature=0.4,
                    max_tokens=1000
                )

                msg = response.choices[0].message

                # If no tool calls -> return final text reply
                if not msg.tool_calls:
                    reply = msg.content or "Task completed successfully!"
                    self.mem.append_conversation(user_name, user_message)
                    self.mem.append_conversation("JARVIS", reply)
                    self.mem.log_task("CHAT_RESPONSE", f"User: {user_message[:60]}... | Reply: {reply[:60]}...")
                    return reply

                # Append assistant tool calls
                messages.append(msg)

                # Execute each tool call
                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        fn_args = {}
                    
                    tool_output = self.execute_tool(fn_name, fn_args)
                    self.mem.log_task("TOOL_EXECUTION", f"Tool: {fn_name}", {"args": fn_args, "output_preview": tool_output[:100]})
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": str(tool_output)
                    })

            # If reached max loop turns, call once more with tools to get final text
            final_res = self._chat_complete(
                messages=messages,
                tools=TOOLS_DEFINITION,
                tool_choice="auto",
                temperature=0.6,
                max_tokens=1000
            )
            final_reply = final_res.choices[0].message.content or "Completed task maapla!"
            self.mem.append_conversation(user_name, user_message)
            self.mem.append_conversation("JARVIS", final_reply)
            return final_reply

        except Exception as e:
            logger.error(f"Error in agent processing: {e}")
            try:
                fallback_res = self.client.chat.completions.create(
                    model=self.fast_model,
                    messages=[
                        {"role": "system", "content": "You are JARVIS. Reply in friendly Tamil-Tanglish."},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.6,
                    max_tokens=500
                )
                fb_reply = fallback_res.choices[0].message.content or "Done maapla!"
                self.mem.append_conversation(user_name, user_message)
                self.mem.append_conversation("JARVIS", fb_reply)
                return fb_reply
            except Exception:
                return f"Jarvis Brain Error: {str(e)}"


if __name__ == "__main__":
    brain = AgentBrain()
    print("AgentBrain prompt updated with pure Tamil-Tanglish!")
