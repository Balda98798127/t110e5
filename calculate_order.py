"""
Решение квадратного уравнения ax^2 + bx + c = 0
Версия: 1.0
Автор: Рахманов И. О.
Дата: 17.10.2026
"""

import math

def read_coefficient(prompt: str) -> float:
    """Запрашивает у пользователя число и возвращает его как float.

    Повторяет запрос, пока не будет введено корректное число.

    Args:
        prompt: Текст приглашения для ввода.

    Returns:
        Введённое число.
    """
    while True:
        try:
            return float(input(prompt).replace(",", "."))
        except ValueError:
            print("Ошибка: введите число.")

def calculate_discriminant(a: float, b: float, c: float) -> float:
    """Вычисляет дискриминант квадратного уравнения.

    Формула: D = b^2 - 4ac

    Args:
        a: Коэффициент при x^2.
        b: Коэффициент при x.
        c: Свободный член.

    Returns:
        Значение дискриминанта.
    """
    return b ** 2 - 4 * a * c

def solve_quadratic_equation(a: float, b: float, c: float) -> tuple:
    """Решает уравнение ax^2 + bx + c = 0.

    Args:
        a: Коэффициент при x^2 (не должен быть равен 0).
        b: Коэффициент при x.
        c: Свободный член.

    Returns:
        Кортеж корней: пустой (нет корней), из одного
        или из двух значений.

    Raises:
        ValueError: Если a == 0 (уравнение не квадратное).
    """
    if a == 0:
        raise ValueError("Коэффициент a не может быть равен 0.")

    discriminant = calculate_discriminant(a, b, c)

    if discriminant < 0:
        # Действительных корней нет
        return ()
    if discriminant == 0:
        # Один корень (кратности 2)
        return (-b / (2 * a),)

    sqrt_d = math.sqrt(discriminant)
    root_1 = (-b + sqrt_d) / (2 * a)
    root_2 = (-b - sqrt_d) / (2 * a)
    return (root_1, root_2)

def main() -> None:
    """Точка входа: ввод коэффициентов, решение и вывод результата."""
    print("Решение уравнения ax^2 + bx + c = 0")
    a = read_coefficient("Введите a: ")
    b = read_coefficient("Введите b: ")
    c = read_coefficient("Введите c: ")

    try:
        roots = solve_quadratic_equation(a, b, c)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return

    if not roots:
        print("Действительных корней нет.")
    elif len(roots) == 1:
        print(f"Один корень: x = {roots[0]}")
    else:
        print(f"Два корня: x1 = {roots[0]}, x2 = {roots[1]}")

if __name__ == "__main__":
    main()

# TODO: добавить поддержку комплексных корней при D < 0.
# TODO: добавить unit-тесты (unittest/pytest).
# FIXME: сравнение discriminant == 0 для float может быть неточным;
#        использовать math.isclose().