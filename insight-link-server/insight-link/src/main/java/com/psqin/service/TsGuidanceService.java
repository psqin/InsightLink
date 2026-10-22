package com.psqin.service;

import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.vo.StudentVO;
import com.psqin.result.PageResult;

import java.util.List;

public interface TsGuidanceService {
    void saveBatch(List<Long> ids);

    void deleteBatch(List<Long> userids);

    PageResult pageQuery(StudentSearchDTO studentSearchDTO);

    StudentVO getStudentDetail(Long studentUserId);
}
