SELECT  id
       ,file_name
       ,file_path
       ,file_md
       ,`type`
       ,created_at
       ,created_by
       ,updated_at
       ,updated_by
FROM app.t_app_extract_md_from_article
WHERE id BETWEEN 1772 AND 1900
AND id = 1793
AND file_name LIKE '%中国气象局气象观测质量管理体系质量手册%'
AND file_md is not null
AND LENGTH(file_md) > 10
ORDER BY id DESC
;

