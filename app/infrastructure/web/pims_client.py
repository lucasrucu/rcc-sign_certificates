import asyncio
from pathlib import Path
import re
from playwright.async_api import async_playwright, Page

from app.domain.enums.document_enums import DocumentDiscipline


class PIMSClient:
    def __init__(self, config: dict, headless: bool, timeout: int):
        self.config = config
        self.headless = headless
        self.timeout = timeout

        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Page | None = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def login(self):
        """
        Login to PIMS (single-page login: username + password, no Next button).
        """
        # Prevent duplicate login
        if getattr(self, "_logged_in", False):
            return

        cfg = self.config["pims"]
        extra_wait = self.config.get("behavior", {}).get("extra_wait", 2) * 1000

        # 1️⃣ Open PIMS login page
        await self.page.goto(
            cfg["login_url"],
            wait_until="domcontentloaded",
            timeout=self.timeout,
        )
        await self.page.wait_for_timeout(extra_wait)

        # 2️⃣ Fill username
        await self.page.locator(
            "input[type='text'], input[name*='user' i], input[id*='user' i]"
        ).first.fill(cfg["username"])

        # 3️⃣ Fill password
        await self.page.locator(
            "input[type='password']"
        ).first.fill(cfg["password"])

        # 4️⃣ Submit login (no Next step)
        await self.page.locator("button.btn-primary").click()

        await self.page.wait_for_timeout(extra_wait)

        self._logged_in = True
        print("✅ Logged into PIMS successfully")
        
    async def upload_document_metadata(self, metadata_path: Path, source_id: str = "dsDocuments"):
        if not metadata_path.exists():
            raise FileNotFoundError(metadata_path)

        # Open ellipsis menu
        ellipsis = self.page.locator("a.px-2 i.fa-ellipsis-v").first
        await ellipsis.wait_for(state="visible", timeout=5000)
        await ellipsis.click()

        # Click Import and capture file chooser
        import_option = self.page.locator(
            f'a.dropdown-item[data-template-import][data-source-id="{source_id}"]'
        )

        async with self.page.expect_file_chooser() as fc:
            await import_option.click()

        file_chooser = await fc.value
        await file_chooser.set_files(str(metadata_path))

        extra_wait = (
            self.config.get("behavior", {}).get("extra_wait", 2) * 1000
        )
        await self.page.wait_for_timeout(extra_wait)
        
        print(f"✅ Uploaded metadata file: {metadata_path.name}")

    
    async def navigate(self, config_key: str):
        """
        Navigate to a PIMS page using a key from config["pims"].
        Example: navigate("documents_url")
        """
        cfg = self.config["pims"]

        if config_key not in cfg:
            raise KeyError(f"PIMS config key not found: {config_key}")

        url = cfg[config_key]

        await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=self.timeout,
        )

        extra_wait = self.config.get("behavior", {}).get("extra_wait", 2) * 1000
        await self.page.wait_for_timeout(extra_wait)
        
        print(f"✅ Navigated to {config_key} page")
        
    async def upload_document_file(self, document_id: str, pdf_path: Path):
        """
        Upload a PDF file for a single document in PIMS.
        Assumes caller has navigated to documents page.
        """

        # Search document
        search_input = self.page.locator(
            "input[autocomplete='af-autocomplete-DocumentID']"
        )
        await search_input.wait_for(state="visible", timeout=self.timeout)
        await search_input.fill(document_id)
        await self.page.keyboard.press("Enter")

        extra_wait = self.config.get("behavior", {}).get("extra_wait", 2) * 1000
        await self.page.wait_for_timeout(extra_wait)

        # Open document detail
        row = self.page.get_by_role("row").filter(has_text=document_id).first
        await row.wait_for(state="visible", timeout=self.timeout)

        link = row.get_by_role("link").first
        async with self.page.context.expect_page() as new_page_info:
            await link.click()

        detail_page = await new_page_info.value
        await detail_page.wait_for_load_state("domcontentloaded")
        
        await asyncio.sleep(3) # wait 3 seconds for any potential modals to appear

        # Check if PDF already exists
        existing_pdf = detail_page.locator(
            "#gridFiles a[data-field='FileName']"
        ).filter(has_text=".pdf")

        if await existing_pdf.count() > 0:
            await detail_page.close()
            return "ALREADY_EXISTS"

        # Upload PDF
        add_btn = detail_page.get_by_role("button", name="Add File")
        await add_btn.wait_for(state="visible", timeout=self.timeout)

        async with detail_page.expect_file_chooser() as fc_info:
            await add_btn.click()

        file_chooser = await fc_info.value
        await file_chooser.set_files(str(pdf_path))

        # Wait for upload completion
        await detail_page.locator("h5.uploadingProgress").wait_for(
            state="visible",
            timeout=10_000,  # initial processing time before progress appears
        )
        await detail_page.locator("h5.uploadingProgress").wait_for(
            state="hidden",
            timeout=7_200_000,  # long uploads
        )

        await detail_page.close()
        return "UPLOADED"
    
    async def prepare_certificates_subsystem_page(self):
        """
        Navigate to certificates page and activate Subsystem tab.
        This is REQUIRED before RFCC actions.
        """
        cfg = self.config["pims"]
        extra_wait = self.config.get("behavior", {}).get("extra_wait", 2) * 1000

        # Robust navigation (PIMS is slow)
        for attempt in range(3):
            try:
                await self.page.goto(
                    cfg["certificates_url"],
                    wait_until="networkidle",
                    timeout=30_000,
                )
                break
            except Exception:
                if attempt == 2:
                    raise
                await self.page.wait_for_timeout(2000)

        # Activate Subsystem tab
        await self.page.locator(
            "a[href='#cmsSubSystem']"
        ).wait_for(state="visible", timeout=15_000)

        await self.page.locator(
            "a[href='#cmsSubSystem']"
        ).first.click()

        await self.page.wait_for_timeout(extra_wait)

        print("✅ Certificates → Subsystem tab ready")
        
    async def sign_rfcc_for_subsystem(
        self,
        subsystem_external_id: str,
        disciplines: set[str],
    ) -> str:
        """
        Execute full RFCC workflow for one subsystem.

        Returns:
            "SIGNED"       → RFCC accepted
            "NOT_FOUND"    → subsystem or RFCC not found
            "FAILED"       → error during process
        """
        
        cfg = self.config
        extra_wait = cfg.get("behavior", {}).get("extra_wait", 2) * 1000
        page = self.page

        # ───────────────────────────────────────────────────────────
        # Search Subsystem
        # ───────────────────────────────────────────────────────────
        search_inputs = page.locator(
            "#cmsSubSystem input[autocomplete='af-autocomplete-SubSystem']:visible"
        )
        if await search_inputs.count() == 0:
            raise RuntimeError("Subsystem search input not found")

        search_input = search_inputs.first
        await search_input.click()
        await search_input.fill("")
        await search_input.fill(subsystem_external_id)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(extra_wait)

        rows = page.get_by_role("row")
        if await rows.count() != 5:
            return "NOT_FOUND"

        # ───────────────────────────────────────────────────────────
        # Open RFCC tab
        # ───────────────────────────────────────────────────────────
        subsystem_tab = page.locator("#cmsSubSystem")
        rfcc_links = subsystem_tab.get_by_role("link", name="RFCC", exact=True)
        if await rfcc_links.count() == 0:
            return "NOT_FOUND"

        async with page.context.expect_page() as new_page_info:
            await rfcc_links.first.click(force=True, timeout=5000)

        rfcc_page = await new_page_info.value
        await rfcc_page.wait_for_load_state("domcontentloaded")
        await rfcc_page.wait_for_timeout(extra_wait)

        # ───────────────────────────────────────────────────────────
        # Already accepted?
        # ───────────────────────────────────────────────────────────
        accepted_badges = rfcc_page.locator("span.badge-success").filter(has_text="Accepted")
        for i in range(await accepted_badges.count()):
            badge = accepted_badges.nth(i)
            hidden = await badge.evaluate(
                "el => el.classList.contains('hide') || "
                "el.classList.contains('d-none') || "
                "el.style.display === 'none'"
            )
            if not hidden:
                await rfcc_page.close()
                return "SIGNED"

        # ───────────────────────────────────────────────────────────
        # Rev Up Certificate (if outdated)
        # ───────────────────────────────────────────────────────────
        warning = rfcc_page.locator("div.alert-warning").filter(has_text="outdated")
        if await warning.count() > 0:
            cert_btn = rfcc_page.locator("button.dropdown-toggle").filter(
                has_text="Certificate"
            ).first
            await cert_btn.click()
            await rfcc_page.wait_for_timeout(600)

            rev_up_cert = rfcc_page.locator(
                "a.dropdown-item", has_text="Rev Up Certificate"
            )
            rev_up_sig = rfcc_page.locator(
                "a.dropdown-item", has_text="Rev Up Signature"
            )

            if await rev_up_cert.count() > 0:
                await rev_up_cert.first.click()
            elif await rev_up_sig.count() > 0:
                await rev_up_sig.first.click()
            else:
                await rfcc_page.close()
                return "FAILED"

            await rfcc_page.wait_for_timeout(800)
            await rfcc_page.locator(
                "button.btn-primary[data-dismiss='modal']"
            ).filter(has_text="Yes").click()

            try:
                await warning.wait_for(state="hidden", timeout=15000)
            except Exception:
                await rfcc_page.wait_for_timeout(3000)

            await rfcc_page.reload(wait_until="domcontentloaded")
            await rfcc_page.wait_for_timeout(extra_wait)
            

        # ───────────────────────────────────────────────────────────
        # Dossier Index
        # ───────────────────────────────────────────────────────────
        await rfcc_page.locator("a#tabDossierIndex").click()
        await rfcc_page.wait_for_timeout(extra_wait)

        row0 = rfcc_page.locator("#dossierTable [data-list-index='0']")
        await row0.wait_for(state="visible", timeout=10000)

        exclude_btn = row0.locator("div[action='excludeFromHandover']")
        if await exclude_btn.count() > 0:
            visible = not await exclude_btn.evaluate(
                "el => el.classList.contains('hide') || el.classList.contains('d-none')"
            )
            if visible:
                await exclude_btn.click(force=True)
                await rfcc_page.wait_for_timeout(800)

        # ───────────────────────────────────────────────────────────
        # Check Items
        # ───────────────────────────────────────────────────────────
        normalized_disciplines = {
            d.value.strip()
            for d in disciplines
            if d != DocumentDiscipline.NO_DISC
        }
            
        await rfcc_page.locator("a#tabBlockCheckItems, a[href='#blockCheckItems']").first.click()
        await rfcc_page.wait_for_timeout(extra_wait)

        rows = rfcc_page.locator("#checkItemsTable [data-list-index]")
        for i in range(await rows.count()):
            row = rows.nth(i)

            item_no = (await row.locator("a[data-field='Item']").text_content() or "").strip()
            desc = (await row.locator("div[data-field='Description']").text_content() or "").strip()

            action_div = row.locator("div[data-function='getCheckItemState']").first
            if await action_div.count() > 0:
                hidden = await action_div.evaluate(
                    "el => el.classList.contains('hide') || el.classList.contains('d-none')"
                )
                if hidden:
                    continue

            if item_no == "1.1":
                action = "OK"
            elif item_no.startswith("2."):
                action = "OK" if desc in normalized_disciplines else "NA"
            else:
                continue

            btn = row.locator(f"div.cl-action-button[action='{action}']").first
            if await btn.count() == 0:
                continue

            already_set = not await btn.evaluate(
                "el => el.classList.contains('not-checked')"
            )
            if already_set:
                continue

            await btn.click(force=True)
            await rfcc_page.wait_for_timeout(500)
            

        # ───────────────────────────────────────────────────────────
        # Signatures
        # ───────────────────────────────────────────────────────────
        async def click_proceed():
            proceed = rfcc_page.locator(
                "button[data-dismiss='modal']:visible"
            ).filter(has_text="Proceed")
            try:
                await proceed.first.wait_for(state="visible", timeout=5000)
                await proceed.first.click()
                await rfcc_page.wait_for_timeout(800)
            except Exception:
                pass

        await rfcc_page.locator("a#tabBlockSignatures").click()
        await rfcc_page.wait_for_timeout(extra_wait)

        for step in [0, 1, 2]:
            btn = rfcc_page.locator(f"button[onclick='signStep({step})']")
            if await btn.count() > 0:
                hidden = await btn.evaluate(
                    "el => el.classList.contains('hidden') || el.style.display === 'none'"
                )
                if not hidden:
                    await btn.click()
                    await click_proceed()
                    await rfcc_page.wait_for_timeout(extra_wait)

        await rfcc_page.reload(wait_until="domcontentloaded")
        await rfcc_page.wait_for_timeout(2000)

        # ───────────────────────────────────────────────────────────
        # Final Accepted check
        # ───────────────────────────────────────────────────────────
        accepted_badges = rfcc_page.locator("span.badge-success").filter(has_text="Accepted")
        for i in range(await accepted_badges.count()):
            badge = accepted_badges.nth(i)
            hidden = await badge.evaluate(
                "el => el.classList.contains('hide') || "
                "el.classList.contains('d-none') || "
                "el.style.display === 'none'"
            )
            if not hidden:
                await rfcc_page.close()
                return "SIGNED"

        await rfcc_page.close()
        return "FAILED"
    