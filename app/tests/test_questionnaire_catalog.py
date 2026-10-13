from app.questionnaire.catalog import QUESTIONS, catalog_response


def test_catalog_has_exact_questions_and_cardinalities():
    assert [q.id for q in QUESTIONS] == [f"q{i}" for i in range(1, 11)]
    assert [q.max_choices for q in QUESTIONS] == [1, 1, 1, 1, 1, 3, 2, 1, 1, 3]
    assert all(q.min_choices == 1 for q in QUESTIONS)
    assert [q.id for q in QUESTIONS if q.selection == "multi"] == ["q6", "q7", "q10"]
    assert catalog_response().questionnaire_version == 1


def test_option_ids_are_unique_and_other_is_only_approved_where_defined():
    for question in QUESTIONS:
        ids = [option.id for option in question.options]
        assert len(ids) == len(set(ids))
        assert all(":" not in option and option == option.strip() for option in ids)
        assert ("other" in ids) == (question.id in {"q1", "q6", "q7"})
