package com.psqin.controller.admin;

import com.psqin.domain.vo.SystemNoticeVO;
import com.psqin.domain.dto.NoticeDTO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.NoticeService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;

@Api(tags = "管理员-通知管理接口")
@RestController("AdminNoticeController")
@RequestMapping("/admin/notice")
@Slf4j
public class NoticeController {

    @Autowired
    private NoticeService noticeService;

    @DeleteMapping("/{id}")
    @ApiOperation("删除通知（管理员可删除所有通知）")
    public Result delete(@PathVariable Long id) {
        noticeService.deleteByAdmin(id);
        return Result.success();
    }

    @PutMapping("/{id}")
    @ApiOperation("修改通知（管理员可修改所有通知）")
    public Result update(@PathVariable Long id, @RequestBody NoticeDTO noticeDTO) {
        noticeService.updateByAdmin(id, noticeDTO);
        return Result.success();
    }

    @GetMapping("/{id}")
    @ApiOperation("通知详情（管理员可查看所有通知）")
    public Result<SystemNoticeVO> getById(@PathVariable Long id) {
        return Result.success(noticeService.getDetailByAdmin(id));
    }

    @GetMapping("/page")
    @ApiOperation("分页查询通知（按发布人姓名、时间筛选）")
    public Result<PageResult> page(
            @RequestParam(required = false) String publisherRealName,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate beginDate,
            @RequestParam(required = false) @DateTimeFormat(pattern = "yyyy-MM-dd") LocalDate endDate,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "10") Integer pageSize
    ) {
        LocalDateTime beginTime = beginDate != null ? beginDate.atStartOfDay() : null;
        LocalDateTime endTime = endDate != null ? endDate.atTime(LocalTime.of(23, 59, 59)) : null;
        return Result.success(noticeService.pageQueryAdmin(publisherRealName, beginTime, endTime, page, pageSize));
    }
}
