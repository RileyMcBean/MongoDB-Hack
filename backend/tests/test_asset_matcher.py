import pytest
from app.asset_matcher import match_asset
from app.models import DataAsset, RiskTier
from app.repositories import DataAssetRepository


@pytest.mark.asyncio
async def test_matches_sales_reporting(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await repo.insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    result = await match_asset(test_db, "I need access to the sales reporting dashboard")
    assert result is not None
    assert result["collection_name"] == "sales_reporting"


@pytest.mark.asyncio
async def test_matches_pii_asset(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales data", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting", "dashboard"],
    ))
    await repo.insert(DataAsset(
        name="Customer PII Dataset", collection_name="customer_pii",
        description="PII data", sensitivity=RiskTier.high,
        required_role="pii_reader", owner="governance",
        tags=["pii", "customer", "sensitive"],
    ))

    result = await match_asset(test_db, "I need access to customer PII records for research")
    assert result is not None
    assert result["collection_name"] == "customer_pii"


@pytest.mark.asyncio
async def test_returns_none_when_no_match(test_db):
    repo = DataAssetRepository(test_db)
    await repo.insert(DataAsset(
        name="Sales Reporting Dashboard", collection_name="sales_reporting",
        description="Sales", sensitivity=RiskTier.low,
        required_role="reporting_reader", owner="team",
        tags=["sales", "reporting"],
    ))

    result = await match_asset(test_db, "I need access to the payroll system")
    assert result is None
