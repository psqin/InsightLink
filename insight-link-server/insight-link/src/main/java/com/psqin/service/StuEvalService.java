package com.psqin.service;

import com.psqin.domain.dto.StuEvalDTO;
import com.psqin.domain.entity.StudentEvaluation;
import com.psqin.domain.dto.StuMatTeaSearchPageDTO;
import com.psqin.result.PageResult;

public interface StuEvalService {
    void save(StuEvalDTO stuEvalDTO);

    void delete(Long id);

    void deleteByAdmin(Long id);

    void update(StuEvalDTO stuEvalDTO);

    StudentEvaluation getById(Long id);

    PageResult pageQueryMaterials(StuMatTeaSearchPageDTO dto);

    PageResult pageQueryMaterialsByAdmin(StuMatTeaSearchPageDTO dto);
}
