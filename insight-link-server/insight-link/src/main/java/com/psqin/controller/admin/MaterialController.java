package com.psqin.controller.admin;

import com.psqin.domain.dto.StuMatTeaSearchPageDTO;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.StuEvalService;
import com.psqin.service.StuMaterialService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "管理员-学生材料与评价管理接口")
@RestController("AdminMaterialController")
@RequestMapping("/admin/material")
@Slf4j
public class MaterialController {

    @Autowired
    private StuMaterialService stuMaterialService;

    @Autowired
    private StuEvalService stuEvalService;

    @GetMapping("/page")
    @ApiOperation("分页查询学生材料与评价")
    public Result<PageResult> page(StuMatTeaSearchPageDTO dto) {
        log.info("管理员分页查询学生材料与评价：{}", dto);
        return Result.success(stuEvalService.pageQueryMaterialsByAdmin(dto));
    }

    @GetMapping("/{id}")
    @ApiOperation("查看材料与评价详情")
    public Result<StudentMaterialVO> getById(@PathVariable Long id) {
        log.info("管理员查看材料与评价：{}", id);
        return Result.success(stuMaterialService.getById(id));
    }

    @DeleteMapping("/{id}")
    @ApiOperation("删除材料（评价一起删除）")
    public Result deleteMaterial(@PathVariable Long id) {
        stuMaterialService.deleteByAdmin(id);
        return Result.success();
    }

    @DeleteMapping("/evaluation/{id}")
    @ApiOperation("删除评价（不删除材料）")
    public Result deleteEvaluation(@PathVariable Long id) {
        stuEvalService.deleteByAdmin(id);
        return Result.success();
    }
}
