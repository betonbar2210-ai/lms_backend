from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from materials.models import Course
from users.models import Payments, Subscriptions, User


class UserPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="pass12345"
        )
        self.moderator = User.objects.create_user(
            email="moderator@example.com", password="pass12345"
        )
        self.moderator.groups.add(Group.objects.create(name="Модераторы"))

        self.course = Course.objects.create(name="Курс", owner=self.owner)
        self.payment = Payments.objects.create(
            user=self.owner, course=self.course, total=1000, method="cash"
        )

    def test_register_and_token_are_public(self):
        response = self.client.post(
            "/users/register/",
            {"email": "new@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json())

        response = self.client.post(
            "/users/token/",
            {"email": "owner@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

        response = self.client.post(
            "/users/token/refresh/", {"refresh": response.json()["refresh"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_token_rejects_invalid_credentials(self):
        response = self.client.post(
            "/users/token/",
            {"email": "owner@example.com", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/users/register/",
            {"email": "weak@example.com", "password": "12345678"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())

    def test_register_rejects_existing_email(self):
        response = self.client.post(
            "/users/register/",
            {"email": "owner@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_register_rejects_existing_email_in_another_case(self):
        response = self.client.post(
            "/users/register/",
            {"email": "OWNER@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertEqual(User.objects.count(), 3)

    def test_users_endpoint_requires_authentication(self):
        self.assertEqual(self.client.get("/users/").status_code, 401)

    def test_users_list_returns_only_public_fields(self):
        self.client.force_authenticate(self.other)

        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)
        self.assertNotIn("payments", response.json()[0])

    def test_any_user_can_view_foreign_profile_without_payments(self):
        self.client.force_authenticate(self.other)

        response = self.client.get(f"/users/{self.owner.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("payments", response.json())

    def test_user_can_view_own_profile_with_payments(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(f"/users/{self.owner.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("payments", response.json())
        self.assertEqual(len(response.json()["payments"]), 1)

    def test_user_can_update_own_profile(self):
        self.client.force_authenticate(self.owner)

        response = self.client.patch(f"/users/{self.owner.id}/", {"city": "Москва"})
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.city, "Москва")

    def test_user_cannot_update_email_to_existing_one(self):
        self.client.force_authenticate(self.owner)

        response = self.client.patch(
            f"/users/{self.owner.id}/", {"email": "OTHER@example.com"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_user_cannot_edit_or_delete_foreign_profile(self):
        self.client.force_authenticate(self.other)

        self.assertEqual(
            self.client.patch(
                f"/users/{self.owner.id}/", {"city": "Взлом"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(f"/users/{self.owner.id}/").status_code, 403
        )

    def test_user_can_delete_own_profile(self):
        self.client.force_authenticate(self.owner)

        response = self.client.delete(f"/users/{self.owner.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.owner.id).exists())

    def test_user_sees_only_own_payments(self):
        Payments.objects.create(
            user=self.other, course=self.course, total=2000, method="transfer"
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get("/users/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["user_email"], self.owner.email)

        self.client.force_authenticate(self.other)
        response = self.client.get("/users/payments/")
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["user_email"], self.other.email)

    def test_moderator_sees_all_payments(self):
        Payments.objects.create(
            user=self.other, course=self.course, total=2000, method="transfer"
        )

        self.client.force_authenticate(self.moderator)
        response = self.client.get("/users/payments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)


class ModeratorGroupFixtureTests(TestCase):
    def test_fixture_loads_moderator_group_with_permissions(self):
        call_command("loaddata", "groups", verbosity=0)

        group = Group.objects.get(name="Модераторы")
        codenames = set(group.permissions.values_list("codename", flat=True))

        self.assertEqual(
            codenames,
            {"view_course", "change_course", "view_material", "change_material"},
        )
        self.assertNotIn("add_course", codenames)
        self.assertNotIn("delete_course", codenames)
        self.assertNotIn("add_material", codenames)
        self.assertNotIn("delete_material", codenames)

    def test_management_command_creates_same_group_permissions(self):
        call_command("create_groups", verbosity=0)

        group = Group.objects.get(name="Модераторы")
        codenames = set(group.permissions.values_list("codename", flat=True))

        self.assertEqual(
            codenames,
            {"view_course", "change_course", "view_material", "change_material"},
        )


class SubscriptionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password="pass12345"
        )
        self.course = Course.objects.create(name="Курс", owner=self.owner)

    def toggle(self, user, payload):
        self.client.force_authenticate(user)
        return self.client.post("/users/subscriptions/", payload)

    def test_toggle_adds_and_removes_subscription(self):
        response = self.toggle(self.other, {"course_id": self.course.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "подписка добавлена"})
        self.assertTrue(
            Subscriptions.objects.filter(user=self.other, course=self.course).exists()
        )

        response = self.toggle(self.other, {"course_id": self.course.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "подписка удалена"})
        self.assertFalse(
            Subscriptions.objects.filter(user=self.other, course=self.course).exists()
        )

    def test_toggle_uses_current_user_and_ignores_foreign_user(self):
        response = self.client.post(
            "/users/subscriptions/",
            {"course_id": self.course.id, "user": self.owner.id},
        )
        self.assertEqual(response.status_code, 401)

        response = self.toggle(
            self.other, {"course_id": self.course.id, "user": self.owner.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Subscriptions.objects.filter(user=self.owner, course=self.course).exists()
        )
        self.assertTrue(
            Subscriptions.objects.filter(user=self.other, course=self.course).exists()
        )

    def test_anonymous_cannot_toggle(self):
        response = self.client.post(
            "/users/subscriptions/", {"course_id": self.course.id}
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Subscriptions.objects.exists())

    def test_missing_course_id_returns_400(self):
        response = self.toggle(self.other, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("course_id", response.json())

    def test_invalid_course_id_returns_400(self):
        response = self.toggle(self.other, {"course_id": 999999})
        self.assertEqual(response.status_code, 400)
        self.assertIn("course_id", response.json())
        self.assertFalse(Subscriptions.objects.exists())

    def test_is_subscribed_in_course_list_and_detail(self):
        Subscriptions.objects.create(user=self.other, course=self.course)
        self.client.force_authenticate(self.other)

        listing = self.client.get("/courses/").json()["results"]
        self.assertEqual(len(listing), 1)
        self.assertTrue(listing[0]["is_subscribed"])

        detail = self.client.get(f"/courses/{self.course.id}/").json()
        self.assertTrue(detail["is_subscribed"])

    def test_is_subscribed_is_false_without_subscription(self):
        self.client.force_authenticate(self.other)

        listing = self.client.get("/courses/").json()["results"]
        self.assertFalse(listing[0]["is_subscribed"])

        detail = self.client.get(f"/courses/{self.course.id}/").json()
        self.assertFalse(detail["is_subscribed"])

    def test_subscription_of_another_user_does_not_leak(self):
        Subscriptions.objects.create(user=self.owner, course=self.course)
        self.client.force_authenticate(self.other)

        listing = self.client.get("/courses/").json()["results"]
        self.assertFalse(listing[0]["is_subscribed"])

        detail = self.client.get(f"/courses/{self.course.id}/").json()
        self.assertFalse(detail["is_subscribed"])

    def test_duplicate_subscription_is_blocked_by_constraint(self):
        Subscriptions.objects.create(user=self.other, course=self.course)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Subscriptions.objects.create(user=self.other, course=self.course)

        self.assertEqual(
            Subscriptions.objects.filter(user=self.other, course=self.course).count(),
            1,
        )
