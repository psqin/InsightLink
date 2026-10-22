package com.psqin.controller.teacher;

import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.vo.StudentVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.TsGuidanceService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 *
 */
@Api(tags = "师生指导相关接口")
@RestController
@RequestMapping("/teacher/ts")
@Slf4j
public class TsGuidanceController {

    @Autowired
    private TsGuidanceService tsGuidanceService;

    /**
     * @param userids 用户id
     * @return
     */
    @PostMapping
    @ApiOperation("学生绑定")
    public Result save(@RequestParam List<Long> userids) {
        log.info("绑定学生用户id：{}",userids);
        tsGuidanceService.saveBatch(userids);
        return Result.success();
    }

    //解绑
    @DeleteMapping
    @ApiOperation("学生解绑")
    public Result delete(@RequestParam List<Long> userids) {
        log.info("解绑学生用户id：{}",userids);
        tsGuidanceService.deleteBatch(userids);
        return Result.success();
    }

    //我的学生查看
    @GetMapping("/page")
    @ApiOperation("我的学生查询")
    public Result<PageResult> page(StudentSearchDTO studentSearchDTO) {
        log.info("查询我的学生：{}", studentSearchDTO);
        PageResult pageResult = tsGuidanceService.pageQuery(studentSearchDTO);
        return Result.success(pageResult);
    }

    @GetMapping("/{id}")
    @ApiOperation("查看单个学生信息")
    public Result<StudentVO> getById(@PathVariable Long id) {
        log.info("查看学生详情：{}", id);
        StudentVO studentVO = tsGuidanceService.getStudentDetail(id);
        return Result.success(studentVO);
    }

}
