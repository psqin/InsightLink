package com.psqin.controller.teacher;

import com.psqin.context.BaseContext;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.dto.TeacherInfoDTO;
import com.psqin.domain.entity.Students;
import com.psqin.domain.entity.Teachers;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.mapper.TeacherMapper;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.StudentService;
import com.psqin.service.TeacherService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 *
 */
@Api(tags = "导师相关接口")
@RestController
@RequestMapping("/teacher")
@Slf4j
public class TeacherController {

    @Autowired
    private TeacherService teacherService;

    /**
     * 信息完善
     */
    @PostMapping
    @ApiOperation("导师信息完善")
    public Result save(@RequestBody TeacherInfoDTO teacherInfoDTO) {
        log.info("信息完善：{}", teacherInfoDTO);
        teacherService.save(teacherInfoDTO);
        return Result.success();
    }

    @PutMapping
    @ApiOperation("导师信息修改")
    public Result update(@RequestBody TeacherInfoDTO teacherInfoDTO) {
        log.info("信息修改：{}", teacherInfoDTO);
        teacherService.update(teacherInfoDTO);
        return Result.success();
    }

    /**
     * 本校本院学生查询
     * @param
     * @return
     */
    @GetMapping("/search")
    @ApiOperation("学生查询")
    public Result<PageResult> page(StudentSearchDTO studentSearchDTO) {
        log.info("学生查询条件：{}",studentSearchDTO);
        PageResult pageResult = teacherService.pageQuery(studentSearchDTO);
        return Result.success(pageResult);
    }

    @GetMapping
    @ApiOperation("查询导师信息")
    public Result<TeacherVO> getTeacherInfo() {
        TeacherVO teacherVO = teacherService.getTeacherInfo();
        return Result.success(teacherVO);
    }

}
