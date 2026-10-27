from django.contrib.auth.models import Group
from rest_framework.test import APITestCase

from materials.models import Course, Material
from users.models import User


class CourseAndMaterialPermissionTests(APITestCase):
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

        self.course = Course.objects.create(name="Курс владельца", owner=self.owner)
        self.material = Material.objects.create(
            name="Урок владельца", course=self.course, owner=self.owner
        )

    def test_anonymous_cannot_create_or_delete(self):
        self.assertEqual(
            self.client.post("/materials/", {"name": "курс"}).status_code, 401
        )
        self.assertEqual(
            self.client.post(
                "/materials/materials/create/", {"name": "урок"}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.delete(f"/materials/{self.course.id}/").status_code, 401
        )
        self.assertEqual(
            self.client.delete(
                f"/materials/materials/delete/{self.material.id}/"
            ).status_code,
            401,
        )

    def test_owner_can_read_update_and_delete_own_objects(self):
        self.client.force_authenticate(self.owner)

        self.assertEqual(self.client.get("/materials/").status_code, 200)
        self.assertEqual(len(self.client.get("/materials/").json()), 1)
        self.assertEqual(
            self.client.get(f"/materials/{self.course.id}/").status_code, 200
        )
        self.assertEqual(self.client.get("/materials/materials/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/materials/materials/{self.material.id}/").status_code,
            200,
        )

        response = self.client.patch(
            f"/materials/{self.course.id}/", {"name": "Новое имя"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["owner"], self.owner.id)

        response = self.client.patch(
            f"/materials/materials/update/{self.material.id}/", {"name": "Новый урок"}
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            self.client.delete(f"/materials/{self.course.id}/").status_code, 204
        )

    def test_create_sets_current_user_as_owner(self):
        self.client.force_authenticate(self.other)

        response = self.client.post("/materials/", {"name": "Мой курс"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Course.objects.get(pk=response.json()["id"]).owner, self.other)

        response = self.client.post(
            "/materials/materials/create/", {"name": "Мой урок"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Material.objects.get(pk=response.json()["id"]).owner, self.other
        )

    def test_user_cannot_read_foreign_objects(self):
        self.client.force_authenticate(self.other)

        self.assertEqual(
            self.client.get(f"/materials/{self.course.id}/").status_code, 404
        )
        self.assertEqual(
            self.client.get(f"/materials/materials/{self.material.id}/").status_code,
            404,
        )
        self.assertEqual(self.client.get("/materials/").json(), [])
        self.assertEqual(self.client.get("/materials/materials/").json(), [])

    def test_user_cannot_update_or_delete_foreign_objects(self):
        self.client.force_authenticate(self.other)

        self.assertEqual(
            self.client.patch(
                f"/materials/{self.course.id}/", {"name": "Взлом"}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                f"/materials/materials/update/{self.material.id}/",
                {"name": "Взлом"},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/materials/{self.course.id}/").status_code, 404
        )
        self.assertEqual(
            self.client.delete(
                f"/materials/materials/delete/{self.material.id}/"
            ).status_code,
            404,
        )

    def test_moderator_can_read_and_edit_any_but_not_create_or_delete(self):
        self.client.force_authenticate(self.moderator)

        self.assertEqual(len(self.client.get("/materials/").json()), 1)
        self.assertEqual(
            self.client.get(f"/materials/{self.course.id}/").status_code, 200
        )
        self.assertEqual(
            self.client.get(f"/materials/materials/{self.material.id}/").status_code,
            200,
        )

        self.assertEqual(
            self.client.patch(
                f"/materials/{self.course.id}/", {"name": "Правка модератора"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(
                f"/materials/materials/update/{self.material.id}/",
                {"name": "Правка модератора"},
            ).status_code,
            200,
        )

        self.assertEqual(
            self.client.post("/materials/", {"name": "Нельзя"}).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                "/materials/materials/create/", {"name": "Нельзя"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(f"/materials/{self.course.id}/").status_code, 403
        )
        self.assertEqual(
            self.client.delete(
                f"/materials/materials/delete/{self.material.id}/"
            ).status_code,
            403,
        )
