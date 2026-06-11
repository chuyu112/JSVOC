import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import AuthAccount, CreditTransaction, LLMChannel, User
from app.services import credit_service
from scripts.configure_kakayiduo_runtime import (
    DEFAULT_BASE_URL,
    configure_kakayiduo_channels,
    ensure_super_admin_target_balance,
    top_up_user_to_balance,
)


class ConfigureKakayiduoRuntimeScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_configures_active_kakayiduo_chat_and_image_channels(self) -> None:
        with self.SessionLocal() as db:
            db.add(
                LLMChannel(
                    name="Old Chat",
                    purpose="chat",
                    provider="mock",
                    base_url="",
                    api_key="",
                    model="mock-model",
                    is_active=True,
                )
            )
            results = configure_kakayiduo_channels(db, api_key="runtime-secret")
            db.commit()

            self.assertEqual({item.purpose for item in results}, {"chat", "image"})
            self.assertTrue(all(item.provider == "kakayiduo" for item in results))
            self.assertTrue(all(item.base_url == DEFAULT_BASE_URL for item in results))
            self.assertTrue(all(item.has_api_key for item in results))

            channels = list(db.scalars(select(LLMChannel)).all())
            active_by_purpose = {
                channel.purpose: [item for item in channels if item.purpose == channel.purpose and item.is_active]
                for channel in channels
            }
            self.assertEqual(active_by_purpose["chat"][0].provider, "kakayiduo")
            self.assertEqual(active_by_purpose["chat"][0].model, "gpt-5.5")
            self.assertEqual(active_by_purpose["image"][0].provider, "kakayiduo")
            self.assertEqual(active_by_purpose["image"][0].model, "gpt-image-2")

    def test_tops_up_named_user_to_target_balance_once(self) -> None:
        with self.SessionLocal() as db:
            user = User(display_name="许卓华")
            db.add(user)
            db.flush()
            db.add(
                AuthAccount(
                    user_id=user.id,
                    provider_type="username",
                    provider_key="xuzhuohua",
                    is_primary=True,
                )
            )
            credit_service.record_transaction(
                db,
                user_id=user.id,
                amount=2000,
                transaction_type="registration_bonus",
                reason="new_user_registration",
                reference_type="user",
                reference_id=user.id,
                commit=False,
            )
            first = top_up_user_to_balance(db, target_user="许卓华", target_balance=20_000)
            second = top_up_user_to_balance(db, target_user="xuzhuohua", target_balance=20_000)
            db.commit()

            self.assertEqual(first.previous_balance, 2000)
            self.assertEqual(first.current_balance, 20_000)
            self.assertEqual(first.granted_amount, 18_000)
            self.assertEqual(second.previous_balance, 20_000)
            self.assertEqual(second.current_balance, 20_000)
            self.assertEqual(second.granted_amount, 0)
            transactions = list(db.scalars(select(CreditTransaction)).all())
            self.assertEqual([item.amount for item in transactions], [2000, 18_000])

    def test_ensures_chuyu111_super_admin_target_balance(self) -> None:
        with self.SessionLocal() as db:
            user = User(display_name="chuyu111")
            db.add(user)
            db.flush()
            db.add(
                AuthAccount(
                    user_id=user.id,
                    provider_type="username",
                    provider_key="chuyu111",
                    is_primary=True,
                )
            )
            credit_service.record_transaction(
                db,
                user_id=user.id,
                amount=2000,
                transaction_type="registration_bonus",
                reason="new_user_registration",
                reference_type="user",
                reference_id=user.id,
                commit=False,
            )

            result = ensure_super_admin_target_balance(db)
            db.commit()

            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.previous_balance, 2000)
            self.assertEqual(result.current_balance, 1_000_000)
            self.assertEqual(result.granted_amount, 998_000)

            credit_service.charge_credits(
                db,
                user_id=user.id,
                cost=1_000,
                reason="video_generation",
                reference_type="generation_task",
                reference_id=123,
                commit=False,
            )
            second = ensure_super_admin_target_balance(db)
            db.commit()

            self.assertIsNotNone(second)
            assert second is not None
            self.assertEqual(second.previous_balance, 999_000)
            self.assertEqual(second.current_balance, 999_000)
            self.assertEqual(second.granted_amount, 0)
            top_up = db.scalars(
                select(CreditTransaction).where(CreditTransaction.transaction_type == "super_admin_top_up")
            ).first()
            self.assertIsNone(top_up)


if __name__ == "__main__":
    unittest.main()
