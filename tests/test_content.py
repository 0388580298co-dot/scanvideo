from apps.worker.services.content import TemplateContentGenerator


def test_template_content_generator_is_deterministic_and_nonempty() -> None:
    package = TemplateContentGenerator().generate("Xin chào mọi người, đây là một video thử nghiệm.")
    assert package.title
    assert package.description
    assert package.hashtags
    assert package.hook
    assert package.cta
