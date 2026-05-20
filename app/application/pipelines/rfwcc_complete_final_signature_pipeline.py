from app.domain.enums.subsystem_enums import SubsystemStatus
from app.domain.models.subsystem import Subsystem
from app.infrastructure.excel.loaders import load_subsystems
from app.infrastructure.excel.writers import write_subsystems
from app.infrastructure.web.pims_client import PIMSClient
from config.secrets import PIMS_CREDENTIALS
from config.settings import PIMS

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}


async def run_rfwcc_complete_final_signature_pipeline():
    """
    Complete only the final signature step for subsystems marked PARTIALLY_SIGNED.
    """
    ss_rows = load_subsystems()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]

    to_complete = [
        s for s in all_subsystems
        if s.rfwcc_status == SubsystemStatus.PARTIALLY_SIGNED
    ]

    if not to_complete:
        print("\n✅ No subsystems pending final RFWCC signature.")
        return

    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()

        batch_counter = 0

        for subsystem in to_complete:
            try:
                result = await client.complete_rfwcc_final_signature(
                    subsystem_external_id=subsystem.external_id,
                )

                if result == "SIGNED":
                    subsystem.rfwcc_status = SubsystemStatus.SIGNED
                    print(f"✅ Final RFWCC signed: {subsystem.external_id}")
                elif result == "NOT_FOUND":
                    subsystem.rfwcc_status = SubsystemStatus.NOT_UPLOADED
                    print(
                        f"⚠ Subsystem not found for RFWCC final step, marked NOT_UPLOADED: "
                        f"{subsystem.external_id}"
                    )
                else:
                    print(f"❌ Final RFWCC signing failed for {subsystem.external_id}: {result}")

            except Exception as e:
                print(f"❌ Error completing final RFWCC for {subsystem.external_id}: {e}")

            finally:
                batch_counter += 1
                if batch_counter >= 3:
                    write_subsystems(all_subsystems)
                    batch_counter = 0

        if batch_counter > 0:
            write_subsystems(all_subsystems)

    print("\n✅ RFWCC final-signature pipeline completed.")
