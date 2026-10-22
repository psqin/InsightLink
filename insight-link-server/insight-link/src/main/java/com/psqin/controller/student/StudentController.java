package com.psqin.controller.student;

import com.psqin.domain.dto.StudentInfoDTO;
import com.psqin.domain.vo.StudentVO;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.result.Result;
import com.psqin.service.StudentService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 *
 */
@Api(tags = "学生相关接口")
@RestController
@RequestMapping("/student")
@Slf4j
public class StudentController {

    @Autowired
    private StudentService studentService;

    @PostMapping
    @ApiOperation("学生信息完善")
    public Result save(@RequestBody StudentInfoDTO studentInfoDTO) {
        log.info("信息完善：{}", studentInfoDTO);
        studentService.save(studentInfoDTO);
        return Result.success();
    }

    @PutMapping
    @ApiOperation("学生信息修改")
    public Result update(@RequestBody StudentInfoDTO studentInfoDTO) {
        log.info("信息修改：{}", studentInfoDTO);
        studentService.update(studentInfoDTO);
        return Result.success();
    }

    @GetMapping
    @ApiOperation("查询学生信息")
    public Result<StudentVO> getStudentInfo() {
        StudentVO studentVO = studentService.getStudentInfo();
        return Result.success(studentVO);
    }

    @GetMapping("/teacher")
    @ApiOperation("查询我的导师信息")
    public Result<TeacherVO> getMyTeacherInfo() {
        TeacherVO teacherVO = studentService.getMyTeacherInfo();
        return Result.success(teacherVO);
    }

}
