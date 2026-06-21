from app.models.entities import CompensationType
from app.core.exceptions import AppError


def validate_compensation(
    compensation_type: CompensationType | None,
    compensation_rate: int | None,
    compensation_percent: int | None,
) -> None:
    if compensation_type is None:
        if compensation_rate is not None or compensation_percent is not None:
            raise AppError("Укажите compensation_type вместе со ставкой")
        return

    if compensation_type == CompensationType.PERCENT:
        if compensation_rate is None or compensation_rate < 1 or compensation_rate > 100:
            raise AppError("Для процента от услуг укажите compensation_rate от 1 до 100")
        if compensation_percent is not None:
            raise AppError("compensation_percent не используется для типа percent")
        return

    if compensation_type == CompensationType.SALARY:
        if compensation_rate is None or compensation_rate < 0:
            raise AppError("Для оклада укажите compensation_rate ≥ 0 (руб.)")
        if compensation_percent is not None:
            raise AppError("compensation_percent не используется для типа salary")
        return

    if compensation_type == CompensationType.SALARY_PLUS_PERCENT:
        if compensation_rate is None or compensation_rate < 0:
            raise AppError("Для оклада укажите compensation_rate ≥ 0 (руб.)")
        if compensation_percent is None or compensation_percent < 1 or compensation_percent > 100:
            raise AppError("Для оклад + % укажите compensation_percent от 1 до 100")
        return

    raise AppError("Неизвестный тип оплаты труда")


def copy_compensation_to_member(member, source) -> None:
    member.compensation_type = source.compensation_type
    member.compensation_rate = source.compensation_rate
    member.compensation_percent = source.compensation_percent
