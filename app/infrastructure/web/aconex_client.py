import asyncio
from pathlib import Path
from typing import Tuple, Optional

from playwright.async_api import async_playwright, Page


DISCIPLINE_MAP_ACONEX = {
    "65 - Electrical": "Electrical",
    "70 - Control Systems": "Telecommunication",
    "59 - Mechanical": "Mechanical",
    "50 - Piping": "Piping",
}


class AconexClient:
    """
    Low-level Playwright client for Aconex document interactions.
    """

    
    def __init__(self, config: dict, downloads_dir: Path, headless: bool, timeout: int):
        self.config = config
        self.downloads_dir = downloads_dir
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._logged_in = False

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless, timeout=self.timeout)
        self.context = await self.browser.new_context(accept_downloads=True)
        self.page = await self.context.new_page()
        print("✅ Playwright launched.")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()
        
    async def _ensure_ag_grid_ready(self, frame):
        if getattr(self, "_ag_grid_ready", False):
            return

        await frame.locator(".ag-root").wait_for(
            state="visible", timeout=20_000
        )

        await frame.wait_for_function(
            """
            () => {
                const rows = document.querySelectorAll(
                    '.ag-center-cols-container .ag-row'
                );
                return rows.length > 0;
            }
            """,
            timeout=20_000,
        )

        # gentle wake‑up interaction
        await frame.locator("div.ag-center-cols-container").click()
        await self.page.wait_for_timeout(200)

        self._ag_grid_ready = True
        
        
    # --------------------------------------------------
    # Authentication
    # --------------------------------------------------
    async def login(self):
        """
        Login to Aconex via Oracle IDCS, select project,
        navigate to Document Search, and reset filters.
        """

        if self._logged_in:
            return

        cfg = self.config["aconex"]
        extra_wait = cfg.get("extra_wait", 2) * 1000

        # ── 1️⃣ Oracle IDCS login ───────────────────────────
        await self.page.goto(cfg["login_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(extra_wait)

        username_sel = (
            'input[name="username"], '
            'input[id="username"], '
            'input[type="email"], '
            'input[autocomplete="username"]'
        )
        await self.page.wait_for_selector(username_sel, timeout=15000)
        await self.page.fill(username_sel, cfg["username"])

        await self.page.click(
            'button:has-text("Next"), button:has-text("Continue"), input[type="submit"]'
        )
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(extra_wait + 3000)

        password_sel = (
            'input[name="password"], '
            'input[id="password"], '
            'input[type="password"]'
        )
        await self.page.wait_for_selector(password_sel, timeout=15000)
        await self.page.fill(password_sel, cfg["password"])

        await self.page.click(
            'button[type="submit"], button:has-text("Sign In"), input[type="submit"]'
        )
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(extra_wait)

        # ── 2️⃣ Select project ─────────────────────────────
        await self.page.goto(cfg["projects_url"], wait_until="domcontentloaded")
        await self.page.wait_for_timeout(extra_wait + 3000)

        project = self.page.locator(f'span[title="{cfg["project_name"]}"]').first
        async with self.page.context.expect_page() as new_page_info:
            await project.click(force=True)

        self.page = await new_page_info.value
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(extra_wait + 3000)

        # ── 3️⃣ Navigate to Document Search ONCE ───────────
        await self.page.locator("li#nav-bar-DOC").click()
        await self.page.wait_for_timeout(1500)

        await self.page.locator("a#nav-bar-DOC-DOC-SEARCH").click()
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(2000)

        # ── 4️⃣ Reset filters ONCE (Angular safe) ──────────
        frame = self.page.frame(name="main")
        if frame:
            await frame.evaluate("""
                const btn = document.querySelector(
                    '.searchActions-item.searchActionButton'
                );
                if (btn) btn.click();
            """)
            await self.page.wait_for_timeout(1500)

        self._logged_in = True
        print("✅ Logged into Aconex successfully and ready for document search")


    # --------------------------------------------------
    # Download & extract
    # --------------------------------------------------
    async def download_document(
        self,
        document_id: str,
    ) -> tuple[Path, Optional[str], Optional[str]]:
        
        print(f"📥 Downloading document {document_id} from Aconex…")

        # --------------------------------------------------
        # Get iframe (must already exist)
        # --------------------------------------------------
        frame = self.page.frame(name="main")
        if frame is None:
            raise RuntimeError("Main iframe not found")
        
        # await self._ensure_ag_grid_ready(frame)

        async def search_and_get_row():
            search_input = frame.locator("input#search-keywords-id")
            await search_input.wait_for(state="visible", timeout=15_000)

            # Clear previous value explicitly
            await search_input.fill("")
            await search_input.fill(document_id)

            try:
                await frame.locator("button#searchButton").click()
            except:
                await search_input.press("Enter")

            # Let grid update
            await self.page.wait_for_timeout(1500)

            row = frame.locator("div.ag-center-cols-container div.ag-row").first
            await row.wait_for(state="visible", timeout=7_000)
            return row

        # --------------------------------------------------
        # Attempt 1: normal search
        # --------------------------------------------------
        try:
            row = await search_and_get_row()
        except Exception:
            print(f"🔁 No result for {document_id}, clearing filters and retrying")

            # --------------------------------------------------
            # Clear all filters via Angular execution
            # --------------------------------------------------
            await frame.evaluate("""
                const btn = document.querySelector(
                    '.searchActions-item.searchActionButton'
                );
                if (btn) btn.click();
            """)
            await self.page.wait_for_timeout(2000)

            # --------------------------------------------------
            # Attempt 2: retry search
            # --------------------------------------------------
            try:
                row = await search_and_get_row()
            except Exception:
                raise RuntimeError(
                    f"Document not found after clearing filters: {document_id}"
                )

        # --------------------------------------------------
        # Extract title
        # --------------------------------------------------
        title = None
        try:
            title = (
                await row.locator('div[col-id="title"] a')
                .first.text_content()
            )
            title = title.strip() if title else None
        except:
            pass

        # --------------------------------------------------
        # Scroll & extract discipline (AG-Grid quirk)
        # --------------------------------------------------
        await frame.evaluate("""
            const viewport = document.querySelector(
                '.ag-body-horizontal-scroll-viewport'
            );
            if (viewport) viewport.scrollLeft += 900;
        """)
        await asyncio.sleep(0.4)

        discipline = None
        try:
            raw_disc = (
                await row.locator('div[col-id="discipline"]').first.text_content()
            )
            raw_disc = raw_disc.strip() if raw_disc else None
            discipline = DISCIPLINE_MAP_ACONEX.get(raw_disc, raw_disc)
        except:
            pass

        # --------------------------------------------------
        # Download file
        # --------------------------------------------------
        download_btn = frame.locator("div.fileTypeTemplate[data-fileurl]").first
        file_url = await download_btn.get_attribute("data-fileurl")

        if not file_url:
            raise RuntimeError("Document has no downloadable file")

        full_url = "https://au1.aconex.com" + file_url
        save_path = self.downloads_dir / f"{document_id}.pdf"

        async with self.page.expect_download(timeout=90_000) as dl_info:
            await self.page.evaluate(f"window.open('{full_url}')")

        download = await dl_info.value
        await download.save_as(save_path)

        return save_path, title, discipline