package com.psqin.service;

import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.dto.AdminTeacherSearchDTO;
import com.psqin.domain.dto.TeacherInfoDTO;
import com.psqin.domain.entity.Teachers;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.result.PageResult;

/**
 *
 */
public interface TeacherService {

    void save(TeacherInfoDTO teacherInfoDTO);

    PageResult pageQuery(StudentSearchDTO studentSearchDTO);

    Teachers getById(Long id);

    /**
     * 获取当前登录导师的信息
     * @return
     */
    TeacherVO getTeacherInfo();

    void update(TeacherInfoDTO teacherInfoDTO);

    PageResult adminPageQuery(AdminTeacherSearchDTO adminTeacherSearchDTO);

    void adminUpdate(Long teacherId, TeacherInfoDTO teacherInfoDTO);

    void adminDelete(Long teacherId);

    TeacherVO adminGetDetail(Long teacherId);
}
