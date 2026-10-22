package com.psqin.service;

import com.psqin.domain.dto.StudentMaterialDTO;
import com.psqin.domain.dto.StudentMaterialPageDTO;
import com.psqin.domain.entity.StudentMaterial;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.result.PageResult;

public interface StuMaterialService {

    void save(StudentMaterialDTO studentMaterialDTO);

    void delete(Long id);

    void deleteByAdmin(Long id);

    void update(StudentMaterialDTO studentMaterialDTO);

    StudentMaterialVO getById(Long id);

    PageResult pageQuery(StudentMaterialPageDTO studentMaterialPageDTO);
}
