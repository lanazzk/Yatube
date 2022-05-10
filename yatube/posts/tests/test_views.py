import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Follow, Group, Post, User
from posts.views import COUNT_POSTS

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


class PostsBaseTest(TestCase):
    """Базовый класс."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()

        cls.user = User.objects.create(username='Anna')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    """Класс для проверки соответствия страниц."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

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
        cls.small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                         b'\x01\x00\x80\x00\x00\x00\x00\x00'
                         b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                         b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                         b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                         b'\x0A\x00\x3B')

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='posts/'
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded)

    def setUp(self):
        self.guest_client = Client()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}
                    ): 'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.post.author}
                    ): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}
                    ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}
                    ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_show_correct_image(self):
        """На странице post_detal отображается верная картинка."""
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})

        response = self.authorized_client.get(url)

        self.assertEqual(response.context.get('one_post').image,
                         'posts/small.gif')

    def test_pages_show_correct_image(self):
        """
        На страницах Index, group_list, profile отображается верная картинка.
        """
        urls_pages_names = [reverse('posts:index'),
                            reverse('posts:group_list',
                                    kwargs={'slug': self.post.group.slug}),
                            reverse('posts:profile',
                                    kwargs={'username': self.post.author})]
        for url in urls_pages_names:
            response = self.authorized_client.get(url)

            for post in response.context['page_obj'].object_list:
                self.assertEqual(post.image, 'posts/small.gif')


class IndexTestCase(TestCase):
    """Класс для проверки Index.view."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create(username='Anna')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        for x in range(13):
            Post.objects.create(text=f'text{x}', author=self.user)
        self.last_post = Post.objects.create(text='last', author=self.user,
                                             group=self.group)
        self.latest_post = Post.objects.latest('id')
        self.url = reverse('posts:index')

    def test_get_success(self):
        r = self.guest_client.get(self.url)

        page_obj = r.context.get('page_obj')

        self.assertEqual(r.status_code, HTTPStatus.OK)
        self.assertIn('Последние обновления', r.context.get('title'))
        self.assertEqual(len(page_obj), COUNT_POSTS)

    def test_last_post_in_index(self):
        """Последний пост появляется на главной странице."""
        self.assertEqual(self.latest_post.pk, self.last_post.pk)


class PostEditTestCase(PostsBaseTest):
    """Класс для проверки Post_edit.view."""
    def setUp(self):
        self.post = Post.objects.create(author=self.user, text='text')
        self.url = reverse('posts:post_edit', kwargs={'post_id': self.post.pk})

    def test_get_success(self):
        """Тест позитивного GET-запроса."""
        response = self.authorized_client.get(self.url)

        form = response.context.get('form')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(form.instance, self.post)

    def test_auth_get(self):
        """Тест неавторизованного пользователя."""
        response = self.guest_client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_success(self):
        """Тест позитивного POST-сценария."""
        new_text = 'new'
        data = dict(
            text=new_text
        )

        response = self.authorized_client.post(self.url, data=data)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.post.refresh_from_db()
        self.assertEqual(self.post.text, new_text)

    def test_post_auth(self):
        """Проверяем что пост недоступен без авторизации."""
        response = self.guest_client.post(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_error(self):
        """Отправляем несуществующую группу."""
        new_text = 'new_text'
        new_group = 'does_not_exist'
        data = dict(
            text=new_text,
            group=new_group,
        )

        response = self.authorized_client.post(self.url, data=data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        error = response.context.get('form').errors
        self.assertIn('Выберите корректный вариант', str(error))


class GroupListTestCase(TestCase):
    """Класс для проверки Group_post.view."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create(username='Anna')

    def setUp(self):
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание')

        self.group2 = Group.objects.create(
            title='Тест группа 2',
            slug='test2',
            description='Тестовое описание',
        )
        for x in range(13):
            Post.objects.create(text=f'text{x}', author=self.user,
                                group=self.group)
        self.last_post = Post.objects.create(text='last', author=self.user,
                                             group=self.group)
        self.latest_post = Post.objects.latest('id')

    def test_get_success(self):
        url = reverse('posts:group_list', kwargs={'slug': self.group.slug})

        response = self.guest_client.get(url)

        page_obj = response.context.get('page_obj')

        self.assertEqual(len(page_obj), COUNT_POSTS)
        self.assertEqual(self.group, response.context.get('group'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_last_post_in_group(self):
        """Пост попал в нужную группу."""
        group_list = Post.objects.filter(group=self.latest_post.group)
        group_list2 = Post.objects.filter(group=self.group2)

        self.assertIn(self.last_post, group_list)
        self.assertNotIn(self.last_post, group_list2)


class ProfileTestCase(TestCase):
    """Класс для проверки Profile.view."""
    def setUp(self):
        self.guest_client = Client()

        self.authorized_client = Client()
        self.user = User.objects.create(username='Vadim')
        self.authorized_client.force_login(self.user)
        for x in range(13):
            Post.objects.create(text=f'text{x}', author=self.user)

        self.last_post = Post.objects.create(text='last', author=self.user)
        self.latest_post = Post.objects.latest('id')
        self.url = reverse('posts:profile',
                           kwargs={'username': self.user.username})

    def test_get_success(self):
        post_count = Post.objects.filter(author=self.user).count()

        response = self.guest_client.get(self.url)
        page_obj = response.context.get('page_obj')

        self.assertEqual(len(page_obj), COUNT_POSTS)
        self.assertEqual(post_count, response.context.get('counter_posts'))
        self.assertEqual(self.user, response.context.get('author'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'posts/profile.html')

    def test_last_post_in_profile(self):
        """Пост попал в профайл пользователя."""
        profile_list = Post.objects.filter(author=self.latest_post.author)

        self.assertIn(self.last_post, profile_list)


class PostDetailTestCase(TestCase):
    """Класс для проверки Post_detail.view."""
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create(username='Anna')
        self.post = Post.objects.create(text='text', author=self.user)
        for x in range(13):
            Post.objects.create(text=f'text{x}', author=self.user)

    def test_get_success(self):
        url = reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        count_post = Post.objects.all().count()

        response = self.guest_client.get(url)

        self.assertEqual(count_post, response.context.get('posts_count'))
        self.assertEqual(self.post, response.context.get('one_post'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, 'posts/post_detail.html')


class PostCreateTestCase(PostsBaseTest):
    """Класс для проверки Post_create.view."""
    def setUp(self):
        self.url = reverse('posts:post_create')
        Post.objects.create(author=self.user, text='txt')
        self.group = Group.objects.create(title='test',
                                          slug='test-slug',
                                          description='Тестовое описание',
                                          )

    def test_auth_get(self):
        """Тест неавторизованного пользователя."""
        response = self.guest_client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_success(self):
        """Позитивный пост запрос."""
        text = 'rex'
        data = dict(
            text=text,
            group=self.group.id
        )

        response = self.authorized_client.post(self.url, data=data,
                                               follow=True)

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_success(self):
        response = self.authorized_client.get(self.url)

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)

                self.assertIsInstance(form_field, expected)
                self.assertTemplateUsed(response, 'posts/create_post.html')
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_error(self):
        """Отправляем пустой текст."""
        new_text = ''
        data = dict(
            text=new_text)

        response = self.authorized_client.post(self.url, data=data)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        error = response.context.get('form').errors
        self.assertIn('Обязательное поле', str(error))


class CacheTestCase(PostsBaseTest):
    """Класс для проверки работоспособности кэширования."""
    def setUp(self):
        self.url = reverse('posts:index')
        self.post = Post.objects.create(author=self.user, text='txt')

    def test_cache_index(self):
        response = self.authorized_client.get(self.url)
        self.post.delete()
        new_response = self.authorized_client.get(self.url)
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        new_response2 = self.authorized_client.get(self.url)
        self.assertNotEqual(response.content, new_response2.content)


class FollowTestCase(TestCase):
    """Класс для проверки сервиса подписок."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='Anna')
        cls.authorized_client1 = Client()
        cls.authorized_client1.force_login(cls.user)

        cls.user2 = User.objects.create(username='Vadim')
        cls.authorized_client2 = Client()
        cls.authorized_client2.force_login(cls.user2)

        cls.user3 = User.objects.create(username='Lena')
        cls.authorized_client3 = Client()
        cls.authorized_client3.force_login(cls.user3)

        for x in range(13):
            Post.objects.create(text=f'text{x}', author=cls.user)
            Post.objects.create(text=f'text{x}', author=cls.user2)

    def test_follow_profile(self):
        """Проверка подписки."""
        url = reverse('posts:profile_follow',
                      kwargs={'username': self.user.username})
        count = Follow.objects.count()
        self.authorized_client2.post(url)
        self.assertEqual(count + 1, Follow.objects.count())

    def test_unfollow_profile(self):
        """Проверка отписки."""
        count = Follow.objects.count()
        url = reverse('posts:profile_unfollow',
                      kwargs={'username': self.user.username})
        Follow.objects.create(user=self.user2, author=self.user)
        self.authorized_client2.post(url)

        self.assertEqual(count, Follow.objects.count())

    def test_follow_index(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан.
        """
        url = reverse('posts:follow_index')
        Follow.objects.create(user=self.user2, author=self.user)
        post = Post.objects.create(text='text', author=self.user)

        response = self.authorized_client2.get(url)

        page_obj = response.context.get('page_obj')

        self.assertEqual(len(page_obj), COUNT_POSTS)
        self.assertIn(post, page_obj.object_list)

    def test_not_follow_index(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто не подписан.
        """
        url = reverse('posts:follow_index')
        post = Post.objects.create(text='text', author=self.user)

        response = self.authorized_client2.get(url)

        self.assertNotIn(post, response.context.get('page_obj').object_list)
