let
    Источник = Excel.Workbook(Web.Contents("https://docs.google.com/spreadsheets/d/e/2PACX-1vTqnAY2DiiyELeS9qkYZdI1wPmvaBRf9UUHY57WT-bmv4ILQCYXZ088A-toPhr1Wq9QCdHh78TF12Xr/pub?output=xlsx"), null, true),
    #"Арт Лайф_Служба питания_Sheet" = Источник{[Item="Табель",Kind="Sheet"]}[Data],
    #"Удаленные верхние строки" = Table.Skip(#"Арт Лайф_Служба питания_Sheet",2),
    #"Повышенные заголовки" = Table.PromoteHeaders(#"Удаленные верхние строки", [PromoteAllScalars=true]),
    #"Строки с примененным фильтром" = Table.SelectRows(#"Повышенные заголовки", each ([Column1] <> null)),
    #"Другие столбцы с отмененным свертыванием" = Table.UnpivotOtherColumns(#"Строки с примененным фильтром", {"Column1", "Column2", "Column3", "Column4", "Column5", "Column6", "Column7"}, "Дата", "Часы"),
    #"Строки с примененным фильтром1" = Table.SelectRows(#"Другие столбцы с отмененным свертыванием", each ([Column1] <> "СНИЛС")),
    #"Строки с примененным фильтром2" = Table.SelectRows(#"Строки с примененным фильтром1", each not Text.Contains([Дата], "Column")),
    #"Измененный тип1" = Table.TransformColumnTypes(#"Строки с примененным фильтром2",{{"Дата", Int64.Type}}),
    #"Измененный тип2" = Table.TransformColumnTypes(#"Измененный тип1",{{"Дата", type date}, {"Часы", type number}}),
    #"Переименованные столбцы" = Table.RenameColumns(#"Измененный тип2",{{"Column1", "СНИЛС"}, {"Column2", "Подразделение"}, {"Column3", "сп-нсп"}, {"Column4", "ФИО"}, {"Column5", "Отдел (служба)"}, {"Column6", "Должность"}, {"Column7", "Статус"}})
in
    #"Переименованные столбцы"