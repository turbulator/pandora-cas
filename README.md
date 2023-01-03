# Home Assistant custom component for Pandora Car Alarm System

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Donate](https://img.shields.io/badge/donate-Yandex-orange.svg)](https://money.yandex.ru/to/41001690673042)

**Русский** | [English](https://github.com/turbo-lab/pandora-cas/blob/master/README_EN.md)

![Pandora](https://raw.githubusercontent.com/turbo-lab/pandora-cas/master/images/pandora.gif)

Автомобиль тоже может быть частью умного дома. С помощью этого компонента вы сможете отслеживать состояние, управлять и автоматизировать свой автомобиль если он оборудован охранной системой Pandora или Pandect. После настройки интеграции ваши автомобили автоматически обнаружатся и добавятся в Home Assistant.

Компонент использует неофициальный API, полученный в результате reverse engineering, к официальному сайту Pandora `https://p-on.ru`. Функциональность компонента, в целом, повторяет функциональность, доступную на сайте или в мобильном приложении. Для настройки Вам следует использовать те же авторизационные данные, что вы используете на сайте Pandora.

На данный момент компонент поддерживает:

- [Device Tracker](#device-tracker): Местоположение автомобиля.
- [Sensors and Binary Sensors](#sensors): Температура, скорость, статус охраны, дверей и т.д.
- [Services](#команды): Команды, например: открыть/закрыть, завести/заглушить и др.

## Установка

1. Установите [HACS](https://hacs.xyz/docs/installation/manual)
1. Перейдите в раздел  HACS -> Integrations
1. Нажмите кнопку "+", расположенную в нижней правой части экрана
1. Наберите "Pandora" для поиска компонента
1. Установите компонент Pandora Car Alarm System
1. Перезапустите Home Assistant

## Настройка

1. Перейдите в раздел Настройки -> Интеграции
1. Обновите кэш браузера комбинацией Shift+F5
1. Наберите "Pandora" для поиска интеграции
1. Выберите Pandora Car Alarm System
1. Введите логин, пароль, а также частоту обновления информации с сайта p-on.ru
1. При необходимотсти задайте помещение для автомобиля
1. Устройства и сенсоры добавятся в Home Assistant
1. При необходимости, в настройках интеграции выберите единицы измерения топлива, источник данных для одометра и его начальные значения. Для актуализации изменений сенсоров потребуется перезапуск Home Assistant.

## Device Tracker

Для каждого автомобиля будет создан объект device_tracker.`PANDORA_ID`, где `PANDORA_ID` уникальный идентификатор автомобиля в системе Pandora. Доступны все обычные действия для Device Tracker: отслеживание местоположения [на карте](https://www.home-assistant.io/lovelace/map/), [треккинг пути](https://www.home-assistant.io/blog/2020/04/08/release-108/#lovelace-map-history), [контроль зон](https://www.home-assistant.io/docs/automation/trigger/#zone-trigger) и т.д.

## Sensors

Для привязки к автомобилю в имени объекта сенсоров используется идентификатор `PANDORA_ID`, в то время как в человеко-читаемом названии используется название автомобиля с сайта Pandora. Это сделано для того, чтобы при изменении названия автомобиля на сайте не менялись имена объектов, а значит не будет необходимости перенастраивать lovelace UI и автоматизации.

| Объект | Назначение | Примечание |
|-|-|-|
| sensor.`PANDORA_ID`_mileage  | Пробег | км |
| sensor.`PANDORA_ID`_fuel_level | Уровень топлива | % или L |
| sensor.`PANDORA_ID`_cabin_temperature | Температура салона | °C |
| sensor.`PANDORA_ID`_engine_temperature | Температура двигателя | °C |
| sensor.`PANDORA_ID`_ambient_temperature | Уличная температура | °C |
| sensor.`PANDORA_ID`_balance | Баланс СИМ-карты | ₽ |
| sensor.`PANDORA_ID`_speed | Скорость | км/ч |
| sensor.`PANDORA_ID`_engine_rpm | Обороты двигателя | ? |
| sensor.`PANDORA_ID`_gsm_level | Уровень сигнала GSM | 0 - 3 |
| sensor.`PANDORA_ID`_battery_voltage | Напряжение аккумулятора | В |
| binary_sensor.`PANDORA_ID`_connection_state | Связь с автомобилем | есть / нет |
| binary_sensor.`PANDORA_ID`_engine_state | Статус двигателя | запущен / заглушен |
| binary_sensor.`PANDORA_ID`_moving | Статус движения | в движении / без движения |
| binary_sensor.`PANDORA_ID`_lock | Статус охраны | под охраной / снят с охраны |
| binary_sensor.`PANDORA_ID`_coolant_heater | Статус предпускового подогревателя | включен / выключен |
| binary_sensor.`PANDORA_ID`_left_front_door | Левая передняя дверь | открыта / закрыта |
| binary_sensor.`PANDORA_ID`_right_front_door | Правая передняя дверь | открыта / закрыта |
| binary_sensor.`PANDORA_ID`_left_back_door | Левая задняя дверь | открыта / закрыта |
| binary_sensor.`PANDORA_ID`_right_back_door | Правая задняя дверь | открыта / закрыта |
| binary_sensor.`PANDORA_ID`_trunk | Багажник | открыт / закрыт |
| binary_sensor.`PANDORA_ID`_hood | Капот | открыт / закрыт |
| binary_sensor.`PANDORA_ID`_parking | Стояночный тормоз (МКПП) или Parking (АКПП) | |
| binary_sensor.`PANDORA_ID`_brakes | Педаль тормоза | нажата / отпущена |

## Команды

Для команд обязательно нужно указывать идентификатор `PANDORA_ID`. Система должна понять какой именно автомобиль должен выполнить команду, если их несколько.

> Внимание! Через 10с после отправки команды будет произведена серия принудительных обновлений состояния автомобиля для более точной фиксации изменения состояния.

| Команда | Действие | Примечание |
|-|-|-|
| pandora_cas.lock | Поставить под охрану |  |
| pandora_cas.unlock | Снять с охраны | Может быть запрещено настройками блока сигнализации |
| pandora_cas.start_engine | Запустить двигатель |  |
| pandora_cas.stop_engine | Остановить двигатель |  |
| pandora_cas.turn_on_ext_channel | Активировать доп. канал | См. [пример использования](https://www.drive2.ru/l/526540176697066100/) |
| pandora_cas.turn_off_ext_channel | Деактивировать доп. канал |  |

### Примеры использования команд

Вкладка с кнопкой запуска двигателя

```yaml
  - badges: []
    cards:
      - hold_action:
          action: call-service
          service: pandora_cas.start_engine
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
    entity_id: binary_sensor.1234567890_engine_state
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
    service: pandora_cas.turn_on_ext_channel
    data_template:
      id: 1234567890
```

## Отказ от ответственности

Данное программное обеспечение никак не связано и не одобрено ООО «НПО Телеметрия», владельца торговой марки Pandora. Используйте его на свой страх и риск. Автор ни при каких обстоятельствах не несет ответственности за порчу или утрату вашего имущества и возможного вреда в отношении третьих лиц.

Все названия брендов и продуктов принадлежат их законным владельцам.
