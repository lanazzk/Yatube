from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from posts.models import Group, Post, User

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Anna')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create(username='Vasya')
        self.authorized_client_vasya = Client()
        self.authorized_client_vasya.force_login(self.user)

    def test_get_guest_client(self):
        """Страницы доступные неавторизованному пользователю."""
        address_http_status = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Anna/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            '/create/': HTTPStatus.FOUND,
            '/posts/1/edit/': HTTPStatus.FOUND,
        }
        for address, status in address_http_status.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)

                self.assertEqual(response.status_code, status)

    def test_authorized_client_get(self):
        """Страницы доступные авторизованному пользователю."""
        address_http_status = {
            '/create/': HTTPStatus.OK,
            '/posts/1/edit/': HTTPStatus.OK,
        }
        for address, status in address_http_status.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)

                self.assertEqual(response.status_code, status)

    def test_redirect_from_edit(self):
        """Авторизованный клиент запрашивает редактирование чужого поста."""
        response = self.authorized_client_vasya.get(
            '/posts/1/edit/', follow=True)

        self.assertRedirects(response, '/posts/1/')

    def test_redirect_from_create(self):
        """Неавторизованный клиент создает пост."""
        response = self.guest_client.get('/create/')

        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Anna/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)

                self.assertTemplateUsed(response, template)
