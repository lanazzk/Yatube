from django.contrib.auth import get_user_model
from django.test import TestCase
from posts.models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    """Class for testing model Post."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, тестовый пост, тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        object_name = PostModelTest.post
        expected_object_name = object_name.text[:15]

        self.assertIn(expected_object_name, str(object_name))

        group_name = PostModelTest.group
        expected_group_name = group_name.title

        self.assertEqual(expected_group_name, str(group_name))
