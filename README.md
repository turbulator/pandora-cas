[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Yandex-orange.svg)](https://money.yandex.ru/to/41001690673042)

# Home Assistant custom component for Pandora Car Alarm System

**Русский** | [English](https://github.com/turbo-lab/pandora-cas/blob/master/README_EN.md)

![Pandora](https://raw.githubusercontent.com/turbo-lab/pandora-cas/master/images/pandora.gif)

Автомобиль тоже может быть частью умного дома. С помощью этого компонента вы сможете отслеживать состояние, управлять и автоматизировать свой автомобиль, если он оборудован охранной системой Pandora. После настройки ваши автомобили автоматически обнаружатся и добавятся в Home Assistant.

Компонент использует неофициальный API, полученный в результате reverse engineering, к официальному сайту Pandora `https://p-on.ru`. Функциональность компонента, в целом, повторяет функциональность, доступную на сайте или в мобильном приложении. Для настройки Вам следует использовать те же авторизационные данные, что вы используете на сайте Pandora.

На данный момент компонент поддерживает:

- [Device Tracker](#device-tracker): Местоположение автомобиля.
- [Sensors and Binary Sensors](#sensors): Температура, скорость, статус охраны, дверей и т.д.
- [Services](#services): Команды, например: открыть/закрыть, завести/заглушить и др.

## Установка

1. Установить [HACS](https://hacs.xyz/docs/installation/manual)
1. Зайти в HACS в управление Custom repositories и добавить URL этого репозитория ```https://github.com/turbo-lab/pandora-cas```, как Integration
1. Установить компонент Pandora Car Alarm System
1. Настроить компонент в файле `configuration.yaml` (см. следующий пункт)
1. Перезапустить Home Assistant

## Настройка

Чтобы активировать компонент, добавьте эти строки в файл `configuration.yaml`:

```yaml
# Фрагмент файла configuration.yaml
pandora-cas:
  username: YOUR_USERNAME
  password: YOUR_PASSWORD
```

Описание конфигурации:

```yaml
pandora-cas:
  (map) (Optional) Настройки компонента Pandora Car Alarm System.

  username:
    (string)(Required): Логин от сайта p-on.ru.

  password:
    (string)(Required): Пароль от сайта p-on.ru.

  polling_interval:
    (integer)(Optional): Интервал обновления информации с сайта. Меньше значение - быстрее обновляется, но потребляет больше траффика. По-умолчанию: 60s, минимум: 10s

```

## Device Tracker

Для каждого автомобиля будет создан объект device_tracker.`PANDORA_ID`, где `PANDORA_ID` уникальный идентификатор автомобиля в системе Pandora. Доступны все обычные действия для Device Tracker: отслеживание местоположения [на карте](https://www.home-assistant.io/lovelace/map/), [треккинг пути](https://www.home-assistant.io/blog/2020/04/08/release-108/#lovelace-map-history), [контроль зон](https://www.home-assistant.io/docs/automation/trigger/#zone-trigger) и т.д.

## Sensors

Для привязки к автомобилю в имени объекта сенсоров используется идентификатор `PANDORA_ID`, в то время как в человеко-читаемом названии используется название автомобиля с сайта Pandora. Это сделано для того, чтобы при изменении названия автомобиля на сайте не менялись имена объектов, а значит не будет необходимости перенастраивать lovelace UI и автоматизации.

| Объект | Назначение | Примечание |
|-|-|-|
| sensor.`PANDORA_ID`_milage  | Пробег | км |
| sensor.`PANDORA_ID`_fuel_level |  | % |
| sensor.`PANDORA_ID`_cabin_temperature | Температура салона | °C |
| sensor.`PANDORA_ID`_engine_temperature | Температура двигателя | °C |
| sensor.`PANDORA_ID`_ambient_temperature | Уличная температура | °C |
| sensor.`PANDORA_ID`_balance | Баланс СИМ-карты | ₽ |
| sensor.`PANDORA_ID`_speed | Скорость | км/ч |
| sensor.`PANDORA_ID`_engine_rpm | Обороты двигателя | ? |
| sensor.`PANDORA_ID`_gsm_level | Уровень сигнала GSM| 0 - 3 |
| sensor.`PANDORA_ID`_battery_voltage | Напряжение аккумулятора | В |
| binary_sensor.`PANDORA_ID`_connection_state | Связь с автомобилем | есть / нет |
| binary_sensor.`PANDORA_ID`_engine_state | Статус двигателя | запущен / заглушен |
| binary_sensor.`PANDORA_ID`_moving | Статус движения | в движении / без движения |
| binary_sensor.`PANDORA_ID`_lock | Статус охраны | под охраной / снят с охраны |
| binary_sensor.`PANDORA_ID`_coolant_heater | Статус предпускового подогревателя | включен / выключен |
| binary_sensor.`PANDORA_ID`_left_front_door | Левая передняя дверь | отрыта / закрыта |
| binary_sensor.`PANDORA_ID`_right_front_door | Правая передняя дверь | отрыта / закрыта |
| binary_sensor.`PANDORA_ID`_left_back_door | Левая задняя дверь | отрыта / закрыта |
| binary_sensor.`PANDORA_ID`_right_back_door | Правая задняя дверь | отрыта / закрыта |
| binary_sensor.`PANDORA_ID`_trunk | Багажник | отрыт / закрыт |
| binary_sensor.`PANDORA_ID`_hood | Капот | отрыт / закрыт |

## Команды

Для команд обязательно нужно указывать идентификатор `PANDORA_ID`. Система должна понять какой именно автомобиль должен выполнить команду, если их несколько.

> Внимание! Через 10с после выполнения команды производится принудительное автоматическое обновление состояния автомобиля.

| Команда | Действие | Примечание |
|-|-|-|
| pandora-cas.lock | Поставить под охрану |  |
| pandora-cas.unlock | Снять с охраны | Может быть запрещено настройками блока сигнализации |
| pandora-cas.start_engine | Запустить двигатель |  |
| pandora-cas.stop_engine | Остановить двигатель |  |
| pandora-cas.turn_on_ext_channel | Активировать доп. канал | См. [пример использования](https://www.drive2.ru/l/526540176697066100/) |
| pandora-cas.turn_off_ext_channel | Деактивировать доп. канал |  |

### Примеры использования команд

Вкладка с кнопкой запуска двигателя

```yaml
  - badges: []
    cards:
      - hold_action:
          action: call-service
          service: pandora-cas.start_engine
          service_data:
            id: 1234567890
        icon: 'mdi:fan'
        name: Запуск двигателя
        show_icon: true
        show_name: true
        tap_action:
          action: more-info
        type: button
    icon: 'mdi:car'
    panel: false
    path: honda_pilot
    title: Honda Pilot
```

Автоматизация включения доп. канала по событию с условиями. Подробнее см. [пример использования](https://www.drive2.ru/l/526540176697066100/).

```yaml
# Фрагмент файла automations.yaml
- id: switch_on_pilot_seat_heaters
  alias: Включить подогрев сидений
  trigger:
    platform: state
    entity_id: binary_sensor.honda_pilot_engine_state
    to: 'on'
  condition:
  - condition: time
    after: 05:58:00
    before: 06:12:00
    weekday:
    - mon
    - tue
    - wed
    - thu
    - fri
  action:
    service: pandora-cas.turn_on_ext_channel
    data_template:
      id: 1234567890
```

## Отказ от ответственности

Данное программное обеспечение никак не связано и не одобрено ООО «НПО Телеметрия», владельца торговой марки Pandora. Используйте его на свой страх и риск. Автор ни при каких обстоятельствах не несет ответственности за порчу или утрату вашего имущества и возможного вреда в отношении третьих лиц.

Все названия брендов и продуктов принадлежат их законным владельцам.
