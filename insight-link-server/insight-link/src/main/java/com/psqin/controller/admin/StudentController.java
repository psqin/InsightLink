package com.psqin.controller.admin;

import com.psqin.domain.dto.AdminStudentSearchDTO;
import com.psqin.domain.dto.StudentInfoDTO;
import com.psqin.domain.vo.StudentVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.StudentService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "管理员-学生管理接口")
@RestController("AdminStudentController")
@RequestMapping("/admin/student")
@Slf4j
public class StudentController {

    @Autowired
    private StudentService studentService;

    @GetMapping("/page")
    @ApiOperation("分页查询学生（含姓名、学校等信息）")
    public Result<PageResult> page(AdminStudentSearchDTO adminStudentSearchDTO) {
        return Result.success(studentService.adminPageQuery(adminStudentSearchDTO));
    }

    @PutMapping("/{id}")
    @ApiOperation("修改学生信息")
    public Result update(@PathVariable Long id, @RequestBody StudentInfoDTO studentInfoDTO) {
        log.info("管理员修改学生信息，studentId：{}，studentInfoDTO：{}", id, studentInfoDTO);
        studentService.adminUpdate(id, studentInfoDTO);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除学生信息")
    public Result delete(@PathVariable Long id) {
        studentService.adminDelete(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("查询学生详情")
    public Result<StudentVO> getById(@PathVariable Long id) {
        return Result.success(studentService.adminGetDetail(id));
    }
}
