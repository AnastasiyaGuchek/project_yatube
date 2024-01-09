from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='test_text',
            group=cls.group,
        )

        cls.form = PostForm()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormTests.user)

        self.group.id = PostFormTests.group.id
        self.post.id = PostFormTests.post.id

    def test_create_post(self):
        """При отправке валидной формы создаётся запись в базе данных."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Введенный текст'}
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile', kwargs={'username': 'auth'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Введенный текст').exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author_edit_post(self):
        """При отправке валидной формы происходит изменение поста."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Изменяем текст', 'group': self.group.id}
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text='Изменяем текст').exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)
