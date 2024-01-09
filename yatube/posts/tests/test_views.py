import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User


class PostsViewsTest(TestCase):
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

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewsTest.user)
        self.post.id = PostsViewsTest.post.id

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test_slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': 'auth'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Проверяем шаблон index.html на правильность контекста."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_page = list(Post.objects.all()[:settings.POSTS_PER_PAGE])
        self.assertEqual(list(response.context['page_obj']), first_page)

    def test_group_list_show_correct_context(self):
        """Проверяем шаблон group_list.html на правильность контекста."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test_slug'})
        )
        first_page = (list(Post.objects.filter(group=self.group)
                      [:settings.POSTS_PER_PAGE]))
        self.assertEqual(list(response.context['page_obj']), first_page)

    def test_profile_show_correct_context(self):
        """Проверяем шаблон profile.html на правильность контекста."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        list_of_posts = (list(Post.objects.filter(author=self.user)
                         [:settings.POSTS_PER_PAGE]))
        self.assertEqual(list(response.context['page_obj']), list_of_posts)

    def test_detail_page_show_correct_context(self):
        """Проверяем шаблон post_detail.html на правильность контекста."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)

    def test_forms_show_correct(self):
        """Проверяем шаблон post_create.html на правильность контекста."""
        context = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.authorized_client.get(reverse_page)
                self.assertIsInstance(
                    response.context.get('form').fields.get('text'),
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context.get('form').fields.get('group'),
                    forms.fields.ChoiceField)

    def test_post_uses_correct_pages(self):
        """Проверяем отображение поста на нужных страницах."""
        fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': 'test_slug'}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': 'auth'}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем, что пост не оказался в несоответствующей группе."""
        fields = {
            reverse(
                'posts:group_list', kwargs={'slug': 'test_slug'}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_comment_by_authorized_client(self):
        """Коммент авторизованного пользователя появился на странице поста."""
        comments_count = Comment.objects.count()
        form_data = {'text': 'Тестовый коммент'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
                        text='Тестовый коммент').exists())

    def test_check_cache(self):
        """Проверка кеша."""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        request_1 = response_1.content
        post_info = Post.objects.get(id=1)
        post_info.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        request_2 = response_2.content
        self.assertTrue(request_1 == request_2)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        request_3 = response_3.content
        self.assertTrue(request_1 != request_3)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        RANDOM_NUMBER_OF_POSTS = 13
        cls.user = User.objects.create(username='TestUser')
        cls.author = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description',
        )
        cls.posts = [
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )
            for i in range(RANDOM_NUMBER_OF_POSTS)
        ]
        Post.objects.bulk_create(cls.posts)

    def test_first_page_contains_ten_records(self):
        """Количество постов на страницах index, group_list, profile
        равно 10.
        """
        POSTS_PER_PAGE = 10
        urls = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test_slug'}),
            reverse(
                'posts:profile', kwargs={'username': 'auth'}
            ),
        )
        for url in urls:
            response = self.client.get(url)
            page_content = len(response.context.get('page_obj').object_list)
            self.assertEqual(page_content, POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        """Страницы index, group_list, profile
        должны отображать по три поста.
        """
        RANDOM_NUMBER_OF_POSTS = 13
        POSTS_PER_PAGE = 10
        COUNT_POSTS_ON_NEXT_PAGE = RANDOM_NUMBER_OF_POSTS - POSTS_PER_PAGE
        urls = (
            reverse('posts:index') + '?page=2',
            reverse(
                'posts:group_list', kwargs={'slug': 'test_slug'}
            ) + '?page=2',
            reverse(
                'posts:profile', kwargs={'username': 'auth'}
            ) + '?page=2',
        )
        for url in urls:
            response = self.client.get(url)
            page_content = len(response.context.get('page_obj').object_list)
            self.assertEqual(page_content, COUNT_POSTS_ON_NEXT_PAGE)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='test_text',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()

    def test_index_and_profile_pages(self):
        """Изображение передается на главную страницу и страницу профайла."""
        templates = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.post.author}),
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                obj = response.context['page_obj'][0]
                self.assertEqual(obj.image, self.post.image)

    def test_group_list_page(self):
        """Изображение передается на страницу группы."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        obj = response.context['page_obj'][0]
        self.assertEqual(obj.image, self.post.image)

    def test_post_detail_page(self):
        """Изображение передается на отдельную страницу поста."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        obj = response.context['post']
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_page(self):
        """Пост с изображением создается в базе данных."""
        self.assertTrue(
            Post.objects.filter(
                text='test_text', image='posts/small.gif').exists()
        )


class TestFollow(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.user_1 = User.objects.create_user(username='TestUser1')
        cls.authorized_client_1 = Client()
        cls.authorized_client_1.force_login(cls.user_1)
        cls.group = Group.objects.create(
            title='test_title',
            slug='test_slug',
            description='test_description'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='test_text',
            group=cls.group
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.user_1)

    def test_follow(self):
        """Авторизованный пользователь может подписаться на авторов."""
        self.authorized_client_1.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        follow_exist = Follow.objects.filter(
            user=TestFollow.user_1,
            author=TestFollow.author).exists()
        self.assertTrue(follow_exist)

    def test_unfollow(self):
        """Авторизованный пользователь может отписаться от авторов."""
        TestFollow.authorized_client_1.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username}))
        TestFollow.authorized_client_1.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}))
        follow_exist = Follow.objects.filter(
            user=TestFollow.user_1,
            author=TestFollow.author).exists()
        self.assertFalse(follow_exist)

    def test_new_post_follow(self):
        """Новая запись пользователя появляется в ленте подписчиков."""
        count_follow = Follow.objects.filter(user=self.user_1).count()
        self.authorized_client_1.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': TestFollow.author.username}
            )
        )
        Post.objects.create(
            author=self.author,
            text='test_text_2',
            group=self.group
        )
        count_follow_new_post = Follow.objects.filter(user=self.user_1).count()
        self.assertEqual(count_follow_new_post, count_follow + 1)

    def test_new_post_not_follow(self):
        """Новая запись не появляется в ленте неподписанных пользователей."""
        count_follow = Follow.objects.filter(user=self.user_1).count()
        self.authorized_client_1.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': TestFollow.author.username}
            )
        )
        Post.objects.create(
            author=self.author,
            text='test_text_3',
            group=self.group
        )
        self.authorized_client_1.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        count_follow_new_post = Follow.objects.filter(user=self.user_1).count()
        self.assertNotEqual(count_follow_new_post, count_follow + 1)
