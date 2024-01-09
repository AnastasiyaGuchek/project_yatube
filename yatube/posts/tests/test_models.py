from django.conf import settings
from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
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
            text='test_text[:settings.NUMBER_OF_SYMBOLS_IN_POST]',
        )

    def test_title_label(self):
        """verbose_name поля title соответствует ожидаемому."""
        test_group = PostModelTest.group
        verbose = test_group._meta.get_field('title').verbose_name
        self.assertEqual(verbose, 'Название')

    def test_title_help_text(self):
        """help_text поля title совпадает соответствует ожидаемому."""
        test_group = PostModelTest.group
        help_text = test_group._meta.get_field('title').help_text
        self.assertEqual(help_text, 'Введите название')

    def test_model_have_correct_object_names(self):
        """Проверяем, что корректность работы __str__."""
        test_post = PostModelTest.post
        expected_object_name = (test_post.text
                                [:settings.NUMBER_OF_SYMBOLS_IN_POST])
        self.assertEqual(expected_object_name, str(test_post))

    def test_model_have_correct_object_names(self):
        """Проверяем, что корректность работы __str__."""
        test_group = PostModelTest.group
        expected_object_name = test_group.title
        self.assertEqual(expected_object_name, str(test_group))
