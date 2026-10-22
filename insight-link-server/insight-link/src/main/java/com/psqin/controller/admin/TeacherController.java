package com.psqin.controller.admin;

import com.psqin.domain.dto.AdminTeacherSearchDTO;
import com.psqin.domain.dto.TeacherInfoDTO;
import com.psqin.domain.vo.TeacherVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.TeacherService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "管理员-导师管理接口")
@RestController("AdminTeacherController")
@RequestMapping("/admin/teacher")
@Slf4j
public class TeacherController {

    @Autowired
    private TeacherService teacherService;

    @GetMapping("/page")
    @ApiOperation("分页查询导师（含姓名、学校等信息）")
    public Result<PageResult> page(AdminTeacherSearchDTO adminTeacherSearchDTO) {
        return Result.success(teacherService.adminPageQuery(adminTeacherSearchDTO));
    }

    @PutMapping("/{id}")
    @ApiOperation("修改导师信息")
    public Result update(@PathVariable Long id, @RequestBody TeacherInfoDTO teacherInfoDTO) {
        log.info("管理员修改导师信息，teacherId：{}，teacherInfoDTO：{}", id, teacherInfoDTO);
        teacherService.adminUpdate(id, teacherInfoDTO);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除导师信息")
    public Result delete(@PathVariable Long id) {
        teacherService.adminDelete(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("查询导师详情")
    public Result<TeacherVO> getById(@PathVariable Long id) {
        return Result.success(teacherService.adminGetDetail(id));
    }
}
