"""
AURA-OS Universal Tool Registry
shared/registry.py - Strongly-typed, routing-aware tool specification.
Unifies Intent Classification, Routing Taxonomy, and Structural Verification.
"""
from typing import Dict, Any, Optional, Type, Callable, List, Tuple
from pydantic import BaseModel, Field
import logging

from shared.protocol import (
    TaskRoute,
    BatteryVitalsPayload,
    HardwareMetricsPayload,
    CaptureScreenshotPayload,
    OpenBrowserUrlPayload,
    LaunchSgcBillingPayload,
    LockWorkstationPayload,
    RunPreapprovedScriptPayload,
    ExecuteHeadlessAntigravityPayload,
    PreapprovedScriptId
)

logger = logging.getLogger("aura_tool_registry")


# =====================================================================
# SERVER-SIDE TOOL INPUT SCHEMAS
# =====================================================================
class ScrapeSpinningMillsInput(BaseModel):
    district: str = Field(default="Karur", description="Target district in Tamil Nadu (e.g., Karur, Tirupur, Coimbatore, Erode, Dindigul)")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of mill contacts to extract")
    yarn_type: Optional[str] = Field(default=None, description="Optional filter: combed, carded, compact, OE, or polyester cotton")


class CheckGmailInterviewRadarInput(BaseModel):
    hours_back: int = Field(default=24, ge=1, le=168, description="How many hours back to scan for interview invitations, OA test links, or recruiter updates")


class TailorPlacementResumeInput(BaseModel):
    job_description: str = Field(min_length=20, description="Full or summarized Job Description to tailor the master resume against")
    target_company: str = Field(description="Name of the company (e.g., Zoho, Capgemini, TCS, IBM)")
    target_role: str = Field(default="AI Engineer", description="Target position title")


class SyncDriveVaultInput(BaseModel):
    file_path: str = Field(description="Relative or absolute path of the local file to backup to Google Drive Mesh")
    target_node: str = Field(default="node_01", description="Target 25GB Drive Mesh node identifier (e.g., node_01 for memory, node_03 for resumes)")


class CreateSgcBillInput(BaseModel):
    customer: str = Field(description="Name of the party/customer (e.g., Bannari Amman Mills, Sri Laxmi Export)")
    variety: str = Field(default="cone winding", description="Variety or yarn process (e.g., cone winding, bleaching, cheese dyeing)")
    count: str = Field(default="10s", description="Yarn count (e.g., 10s, 20s, 2/10s, 2/40s)")
    kattu: float = Field(default=0.0, description="Quantity in Kattu (bundles)")
    kazhi: float = Field(default=0.0, description="Quantity in Kazhi (hanks)")
    rate: float = Field(description="Rate per Kattu or unit in INR")
    po_no: Optional[str] = Field(default="", description="Optional Purchase Order number")
    party_gst: Optional[str] = Field(default="", description="Optional customer GSTIN number")


class ExecutePythonCodeInput(BaseModel):
    code: str = Field(description="Python code to execute inside the server container sandbox")
    task_label: Optional[str] = Field(default="cloud_task", description="Label for the execution sandbox")


# =====================================================================
# TOOL METADATA & REGISTRATION CONTAINER
# =====================================================================
class ToolMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        route: TaskRoute,
        category: str,
        input_schema: Type[BaseModel],
        structural_validator: Optional[Callable[[Dict[str, Any]], Tuple[bool, str]]] = None,
        requires_semantic_verification: bool = False
    ):
        self.name = name
        self.description = description.strip()
        self.route = route
        self.category = category
        self.input_schema = input_schema
        self.structural_validator = structural_validator
        self.requires_semantic_verification = requires_semantic_verification

    def to_llm_declaration(self) -> Dict[str, Any]:
        """Exports to standard OpenAI / Groq / Gemini function declaration schema with $defs dereferencing."""
        json_schema = self.input_schema.model_json_schema()
        defs = json_schema.get("$defs", {})
        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        # Dereference any $defs into properties directly for strict Groq/OpenAI compatibility
        cleaned_props = {}
        for prop_name, prop_val in properties.items():
            if isinstance(prop_val, dict) and "$ref" in prop_val:
                ref_key = prop_val["$ref"].split("/")[-1]
                if ref_key in defs:
                    resolved = dict(defs[ref_key])
                    # Preserve field description if present in outer schema
                    if "description" in prop_val:
                        resolved["description"] = prop_val["description"]
                    cleaned_props[prop_name] = resolved
                else:
                    cleaned_props[prop_name] = dict(prop_val)
            else:
                cleaned_props[prop_name] = dict(prop_val)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"[{self.route.value.upper()}] {self.description}",
                "parameters": {
                    "type": "object",
                    "properties": cleaned_props,
                    "required": required
                }
            }
        }


# =====================================================================
# UNIVERSAL TOOL REGISTRY CLASS
# =====================================================================
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._register_default_tools()

    def register(
        self,
        name: str,
        description: str,
        route: TaskRoute,
        category: str,
        input_schema: Type[BaseModel],
        structural_validator: Optional[Callable[[Dict[str, Any]], Tuple[bool, str]]] = None,
        requires_semantic_verification: bool = False
    ):
        tool = ToolMetadata(
            name=name,
            description=description,
            route=route,
            category=category,
            input_schema=input_schema,
            structural_validator=structural_validator,
            requires_semantic_verification=requires_semantic_verification
        )
        self._tools[name] = tool
        logger.debug(f"Registered tool '{name}' on route '{route.value}' (Semantic Check: {requires_semantic_verification})")

    def get(self, name: str) -> Optional[ToolMetadata]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        return list(self._tools.values())

    def to_llm_function_declarations(self) -> List[Dict[str, Any]]:
        """Returns the full unified tool catalog for LLM function calling."""
        return [tool.to_llm_declaration() for tool in self._tools.values()]

    def validate_input(self, name: str, raw_params: Dict[str, Any]) -> BaseModel:
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return tool.input_schema.model_validate(raw_params)

    def verify_structural_output(self, name: str, result_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Deterministic Layer 1 check: Verifies output shape without calling LLM."""
        tool = self.get(name)
        if not tool or not tool.structural_validator:
            # If no custom validator, default to non-empty result check
            is_valid = bool(result_data)
            note = "Result contains data" if is_valid else "Empty result data"
            return is_valid, note
        return tool.structural_validator(result_data)

    def _register_default_tools(self):
        # -------------------------------------------------------------
        # LOCAL SYSTEM TOOLS (Physical Laptop Execution)
        # -------------------------------------------------------------
        self.register(
            name="get_battery_vitals",
            description="Check Mukil's laptop battery percentage, power plug state, and discharge status.",
            route=TaskRoute.LOCAL_SYSTEM,
            category="hardware",
            input_schema=BatteryVitalsPayload,
            structural_validator=lambda d: (
                "battery_percent" in d or "percent" in d,
                f"Battery reading: {d.get('battery_percent', d.get('percent', 'unknown'))}%"
            )
        )

        self.register(
            name="get_hardware_metrics",
            description="Get real-time CPU utilization, RAM usage, and available disk storage on Mukil's laptop.",
            route=TaskRoute.LOCAL_SYSTEM,
            category="hardware",
            input_schema=HardwareMetricsPayload,
            structural_validator=lambda d: (
                "cpu_percent" in d and "ram_percent" in d,
                f"CPU: {d.get('cpu_percent')}%, RAM: {d.get('ram_percent')}%"
            )
        )

        self.register(
            name="capture_screenshot",
            description="Capture an instant high-resolution screenshot of Mukil's current laptop screen display.",
            route=TaskRoute.LOCAL_SYSTEM,
            category="hardware",
            input_schema=CaptureScreenshotPayload,
            structural_validator=lambda d: (
                bool(d.get("screenshot_path")) and d.get("size_bytes", 1) > 1000,
                f"Screenshot captured at: {d.get('screenshot_path')}"
            )
        )

        self.register(
            name="open_browser_url",
            description="Open an authenticated web page, link, or portal on Mukil's laptop desktop browser (HTTP/HTTPS only).",
            route=TaskRoute.LOCAL_SYSTEM,
            category="os",
            input_schema=OpenBrowserUrlPayload,
            structural_validator=lambda d: (d.get("opened", False) is True, "Browser launched successfully")
        )

        self.register(
            name="execute_headless_antigravity",
            description="Trigger the autonomous Antigravity software engineer on Mukil's PC to inspect files, edit code, run terminal commands, and fix bugs.",
            route=TaskRoute.LOCAL_SYSTEM,
            category="engineering",
            input_schema=ExecuteHeadlessAntigravityPayload,
            structural_validator=lambda d: (
                d.get("exit_code") == 0 or d.get("success") is True,
                f"Antigravity run finished with exit code {d.get('exit_code', 0)}"
            ),
            requires_semantic_verification=True
        )

        self.register(
            name="run_preapproved_script",
            description="Run a strictly pre-vetted safe maintenance script (check_disk_health, cleanup_temp_files, sgc_backup_snapshot).",
            route=TaskRoute.LOCAL_SYSTEM,
            category="os",
            input_schema=RunPreapprovedScriptPayload,
            structural_validator=lambda d: (d.get("success") is True, f"Script {d.get('script_id')} completed")
        )

        # -------------------------------------------------------------
        # SERVER CLOUD TOOLS (24/7 Online Execution)
        # -------------------------------------------------------------
        self.register(
            name="scrape_spinning_mills",
            description="Search and scrape B2B spinning and textile mills across Tamil Nadu (Karur, Tirupur, Coimbatore, Erode) to collect owner names and phone numbers for SGC.",
            route=TaskRoute.SERVER,
            category="business",
            input_schema=ScrapeSpinningMillsInput,
            structural_validator=lambda d: (
                len(d.get("mills", [])) > 0,
                f"Scraped {len(d.get('mills', []))} mill contacts"
            ),
            requires_semantic_verification=True
        )

        self.register(
            name="check_gmail_interview_radar",
            description="Scan Mukil's Gmail inbox for assessment test links, interview invites, or recruiter updates from companies (Zoho, Capgemini, TCS, etc.).",
            route=TaskRoute.SERVER,
            category="career",
            input_schema=CheckGmailInterviewRadarInput,
            structural_validator=lambda d: (
                "emails_scanned" in d,
                f"Scanned {d.get('emails_scanned', 0)} emails, found {len(d.get('actionable_emails', []))} actionable leads"
            )
        )

        self.register(
            name="tailor_placement_resume",
            description="Analyze a target job description and generate an ATS-optimized tailored resume (>90% score match) based on Mukil's master resume.",
            route=TaskRoute.SERVER,
            category="career",
            input_schema=TailorPlacementResumeInput,
            structural_validator=lambda d: (
                d.get("ats_score", 0) >= 80,
                f"Resume tailored with ATS match score: {d.get('ats_score')}%"
            ),
            requires_semantic_verification=True
        )

        self.register(
            name="sync_drive_vault",
            description="Upload audit reports, scraped data, or memory state files to Mukil's 250GB Google Drive Master Vault mesh.",
            route=TaskRoute.SERVER,
            category="storage",
            input_schema=SyncDriveVaultInput,
            structural_validator=lambda d: (
                bool(d.get("drive_link") or d.get("file_id")),
                f"Drive file synced: {d.get('drive_link', 'ID present')}"
            )
        )

        self.register(
            name="create_sgc_bill",
            description="Create an official Sri Ganapathi Colours (SGC) GST tax invoice, calculate CGST/SGST, generate official A4 PDF, and upload directly to Google Drive Main Bills Vault (11KMBP0HHa2AFl30zjL8-a_-BQk9MgWM9).",
            route=TaskRoute.SERVER,
            category="business",
            input_schema=CreateSgcBillInput,
            structural_validator=lambda d: (
                bool(d.get("billNo")) and d.get("netAmount", 0) > 0,
                f"SGC Bill #{d.get('billNo')} created for ₹{d.get('netAmount')}"
            ),
            requires_semantic_verification=True
        )

        self.register(
            name="execute_python_code",
            description="Execute dynamic Python code inside the server container sandbox, perform calculations, data processing, or generate files, and return stdout/stderr.",
            route=TaskRoute.SERVER,
            category="engineering",
            input_schema=ExecutePythonCodeInput,
            structural_validator=lambda d: (
                d.get("status") == "success" or bool(d.get("stdout")),
                f"Code execution status: {d.get('status')}"
            )
        )


# Global Singleton Instance
registry = ToolRegistry()
