from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='TestUser')
        cls.author = User.objects.create(username='TestAuthor')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )

        cls.post = Post.objects.create(
            author=cls.author,
            text='test_text',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client_author = Client()

        self.authorized_client.force_login(PostURLTests.user)
        self.authorized_client_author.force_login(PostURLTests.author)

        self.post.id = PostURLTests.post.id

    def test_pages_url_exists_at_desired_location(self):
        """Страницы, доступные любому пользователю."""
        url_names = [
            '/',
            '/group/test_slug/',
            '/profile/TestAuthor/',
            f'/posts/{self.post.id}/',
        ]
        for address in url_names:
            with self.subTest(address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_login(self):
        """Страница /create/ перенаправит анонимного пользователя
        на страницу логина.
        """
        url = reverse('users:login')
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, f'{url}?next=/create/')

    def test_posts_post_id_edit_url_redirect_login(self):
        """Страница /posts/post_id/edit/ перенаправит анонимного пользователя
        на страницу логина.
        """
        url = reverse('users:login')
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response, (f'{url}?next=/posts/{self.post.id}/edit/')
        )

    def test_create_url_exists_at_desired_location_for_authorized_user(self):
        """Страница /create/ доступна только авторизованному пользователю."""
        response = self.authorized_client.get('/create/', follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_posts_post_id_edit_url_exists_at_author(self):
        """Страница /posts/post_id/edit/ доступна только автору."""
        response = (self.authorized_client_author.get
                    (f'/posts/{self.post.id}/edit/'))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': '/',
            'posts/group_list.html': '/group/test_slug/',
            'posts/profile.html': '/profile/TestAuthor/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
            'posts/create_post.html': '/create/',
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_posts_post_id_edit_url_redirect_post_detail(self):
        """Страница /posts/post_id/edit/ перенаправит авторизованного
        пользователя (не автора) на страницу поста.
        """
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/', follow=True
        )
        self.assertRedirects(
            response, (f'/posts/{self.post.id}/')
        )

    def test_unexisting_page_at_desired_location(self):
        """Несуществующая страница."""
        response = self.guest_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
