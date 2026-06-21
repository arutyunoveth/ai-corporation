from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response

from src.modules.tender_operator_agent_demo.schemas import (
    TenderOperatorDemoReportResponse,
    TenderOperatorDemoRunResponse,
    TenderOperatorDemoStepsResponse,
    TenderOperatorUploadedRunAnalyzeResponse,
    TenderOperatorUploadedRunCreateResponse,
    TenderOperatorUploadedRunListResponse,
    TenderOperatorUploadedRunResponse,
    TenderOperatorUploadedRunStepsResponse,
)
from src.modules.tender_operator_agent_demo.service import (
    ASSET_MAP,
    get_demo_asset_response,
    get_tender_operator_demo_report,
    get_tender_operator_demo_report_download,
    get_tender_operator_demo_run,
    get_tender_operator_demo_steps,
    render_tender_operator_demo_report_html,
)
from src.modules.tender_operator_agent_demo.ui import render_tender_operator_console_html
from src.modules.tender_operator_agent_demo.upload_service import (
    analyze_uploaded_demo_run,
    create_uploaded_demo_run,
    get_uploaded_demo_report,
    get_uploaded_demo_report_download,
    get_uploaded_demo_report_html,
    get_uploaded_demo_run,
    get_uploaded_demo_run_steps,
    list_uploaded_demo_runs,
)


router = APIRouter(tags=["tender-operator-agent-demo"])


@router.get("/demo/tender-agent", response_class=HTMLResponse)
def tender_operator_demo_page() -> str:
    return render_tender_operator_console_html()


@router.get("/demo/tender-agent/runs/{run_id}", response_class=HTMLResponse)
def tender_operator_uploaded_run_page(run_id: str) -> str:
    return render_tender_operator_console_html(selected_run_id=run_id)


@router.get("/demo/tender-agent/report", response_class=HTMLResponse)
def tender_operator_demo_report_page() -> str:
    return render_tender_operator_demo_report_html()


@router.get("/demo/tender-agent/runs/{run_id}/report", response_class=HTMLResponse)
def tender_operator_uploaded_run_report_page(run_id: str) -> str:
    return get_uploaded_demo_report_html(run_id)


@router.get("/demo/tender-agent/assets/{asset_name}")
def tender_operator_demo_asset(asset_name: str):
    if asset_name not in ASSET_MAP:
        raise HTTPException(status_code=404, detail="Asset was not found")
    return get_demo_asset_response(asset_name)


@router.get("/api/demo/tender-agent/run", response_model=TenderOperatorDemoRunResponse)
def tender_operator_demo_run() -> TenderOperatorDemoRunResponse:
    return get_tender_operator_demo_run()


@router.get("/api/demo/tender-agent/steps", response_model=TenderOperatorDemoStepsResponse)
def tender_operator_demo_steps() -> TenderOperatorDemoStepsResponse:
    return get_tender_operator_demo_steps()


@router.get("/api/demo/tender-agent/report", response_model=TenderOperatorDemoReportResponse)
def tender_operator_demo_report() -> TenderOperatorDemoReportResponse:
    return get_tender_operator_demo_report()


@router.get("/api/demo/tender-agent/report/download")
def tender_operator_demo_report_download() -> Response:
    file_name, payload = get_tender_operator_demo_report_download()
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.post("/api/demo/tender-agent/runs", response_model=TenderOperatorUploadedRunCreateResponse)
async def create_tender_operator_uploaded_run(
    tender_title: str = Form(...),
    tender_category: str = Form(default="Электротехническое оборудование"),
    customer_name: str = Form(default="Промышленный заказчик"),
    notes: str | None = Form(default=None),
    target_margin_percent: float = Form(default=15),
    logistics_reserve_percent: float = Form(default=3),
    risk_reserve_percent: float = Form(default=5),
    payment_delay_days: int = Form(default=45),
    files: list[UploadFile] = File(...),
) -> TenderOperatorUploadedRunCreateResponse:
    uploads: list[tuple[str, str, bytes]] = []
    for item in files:
        uploads.append((item.filename or "upload.bin", item.content_type or "application/octet-stream", await item.read()))
    return create_uploaded_demo_run(
        tender_title=tender_title,
        tender_category=tender_category,
        customer_name=customer_name,
        notes=notes,
        target_margin_percent=target_margin_percent,
        logistics_reserve_percent=logistics_reserve_percent,
        risk_reserve_percent=risk_reserve_percent,
        payment_delay_days=payment_delay_days,
        uploads=uploads,
    )


@router.get("/api/demo/tender-agent/runs", response_model=TenderOperatorUploadedRunListResponse)
def list_tender_operator_uploaded_runs() -> TenderOperatorUploadedRunListResponse:
    return list_uploaded_demo_runs()


@router.get("/api/demo/tender-agent/runs/{run_id}", response_model=TenderOperatorUploadedRunResponse)
def get_tender_operator_uploaded_run(run_id: str) -> TenderOperatorUploadedRunResponse:
    return get_uploaded_demo_run(run_id)


@router.post("/api/demo/tender-agent/runs/{run_id}/analyze", response_model=TenderOperatorUploadedRunAnalyzeResponse)
def analyze_tender_operator_uploaded_run(run_id: str) -> TenderOperatorUploadedRunAnalyzeResponse:
    return analyze_uploaded_demo_run(run_id)


@router.get("/api/demo/tender-agent/runs/{run_id}/steps", response_model=TenderOperatorUploadedRunStepsResponse)
def get_tender_operator_uploaded_run_steps(run_id: str) -> TenderOperatorUploadedRunStepsResponse:
    return get_uploaded_demo_run_steps(run_id)


@router.get("/api/demo/tender-agent/runs/{run_id}/report", response_model=TenderOperatorDemoReportResponse)
def get_tender_operator_uploaded_run_report(run_id: str) -> TenderOperatorDemoReportResponse:
    return get_uploaded_demo_report(run_id)


@router.get("/api/demo/tender-agent/runs/{run_id}/report/download")
def download_tender_operator_uploaded_run_report(run_id: str):
    return get_uploaded_demo_report_download(run_id)
