package com.psqin.service;

import com.psqin.domain.dto.StudentInfoDTO;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.dto.AdminStudentSearchDTO;
import com.psqin.domain.vo.StudentVO;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.result.PageResult;

public interface StudentService {
    void save(StudentInfoDTO studentInfoDTO);

    PageResult pageQuery(StudentSearchDTO studentSearchDTO, Long universityId, Long deptId);

    /**
     * 获取当前登录学生的信息
     * @return
     */
    StudentVO getStudentInfo();

    TeacherVO getMyTeacherInfo();

    void update(StudentInfoDTO studentInfoDTO);

    PageResult adminPageQuery(AdminStudentSearchDTO adminStudentSearchDTO);

    void adminUpdate(Long studentId, StudentInfoDTO studentInfoDTO);

    void adminDelete(Long studentId);

    StudentVO adminGetDetail(Long studentId);
}
