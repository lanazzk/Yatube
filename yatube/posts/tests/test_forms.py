import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Group, Post, User

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsBaseTest(TestCase):
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


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CreateFormTestCase(PostsBaseTest):
    """Класс для проверки создания поста."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.url = reverse('posts:post_create')
        self.count_post = Post.objects.all().count()

    def test_create_post(self):
        form_data = {
            'text': 'rex',
            'group': self.group.id,
            'image': self.uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        last_post = Post.objects.latest('id')

        self.assertEqual(form_data['text'], last_post.text)
        self.assertEqual(Post.objects.all().count(),
                         self.count_post + 1, 'Не удалось создать новый пост')
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': last_post.author}))
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                image='posts/small.gif'
            ).exists()
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostEditFormTestCase(PostsBaseTest):
    """Класс для проверки редактирования поста."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.post = Post.objects.create(text='text',
                                        author=self.user)
        self.url = reverse('posts:post_edit',
                           kwargs={'post_id': self.post.pk})

    def test_edit_post(self):
        new_text = 'new'
        data = {
            'text': new_text,
            'group': self.group.id,
            'image': self.uploaded,
        }

        response = self.authorized_client.post(self.url, data=data)

        self.post.refresh_from_db()
        post_edited = Post.objects.get(id=self.post.pk)

        self.assertEqual(post_edited.text, new_text)
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': post_edited.pk}))
        self.assertTrue(
            Post.objects.filter(
                text=new_text,
                image='posts/small.gif'
            ).exists()
        )


class CommentAddFormTestCase(PostsBaseTest):
    """Класс для проверки добавления комментария."""

    def setUp(self) -> None:
        self.post = Post.objects.create(text='text',
                                        author=self.user)
        self.url = reverse('posts:add_comment',
                           kwargs={'post_id': self.post.pk})

    def test_add_comment(self):
        """Комментарий появляется на странице поста."""
        test_comment = 'My comment'
        data = {'text': test_comment, }

        response = self.authorized_client.post(self.url, data=data,
                                               follow=True)

        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': self.post.pk}))

        comment = Comment.objects.get(post=self.post)

        self.assertTrue(Comment.objects.filter(text=test_comment,
                        id=comment.id).exists())

    def test_guest_client_add_comment(self):
        """Неавторизованный пользователь не может добавить комментарий."""
        guest_client = Client()

        response = guest_client.get(self.url)

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
